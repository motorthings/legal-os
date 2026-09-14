"""Phase 2 — research harvester + admission gate + Voyage indexing.

This is the "go get the latest docs, scrutinize which to add, index them" layer.
It is intentionally a documented seam: the radar runs fully without it (v1 reads
the curated feed.jsonl). Turn it on with `run.py --ingest` once wired.

DESIGN — three stages, allowlist-first so the KB never fills with noise:

  1. HARVEST (allowlist only, never open-web crawl)
     Pull candidate docs from a fixed set of trusted, tiered sources:
       T1  CourtListener / RECAP (opinions, sanctions orders), Federal Register,
           EUR-Lex (EU AI Act), state legislature feeds (Colorado AI Act)
       T2  ABA ethics-opinion index, state bar ethics pages, court standing orders
       T3  Damien Charlotin hallucination tracker, Stanford HAI, carrier bulletins
       T4  LawSites, Artificial Lawyer, major-firm client-alert RSS
     Each source is pre-assigned a tier by domain, so authority is set at intake,
     not guessed later. New/unknown domains go to quarantine, never straight in.

  2. ADMISSION GATE (scrutinize — the anti-noise step)
     A candidate is admitted only if it clears ALL of:
       - tier assigned (known allowlisted source)
       - relevance: matches >=1 fault-line signal AND embedding cosine >= REL_MIN
         to that fault line's centroid
       - novelty: max cosine to existing KB items < DEDUP_MAX (reject near-dupes,
         e.g. the same ruling re-reported by five outlets — keep the primary, drop
         the echoes; echoes still count toward corroboration via a lightweight ref)
       - independence: if the source sells the tool it discusses, set conflict=True
         (weight is discounted downstream, not rejected)
     Every decision (admit / quarantine / dedup) is logged with its reason.

  3. INDEX (Voyage AI -> Supabase pgvector)
     Embed admitted docs with `voyage-law-2` (Voyage's legal-domain model; stronger
     on case law / statutes than general embeddings). Store vectors in Supabase
     pgvector alongside the governance tables legal-os already uses. Embeddings
     power stage-2 relevance + dedup and future semantic retrieval for a forecast
     agent.

Admitted items are appended to sources/feed.jsonl in the same schema v1 already
scores, so the deterministic scorer is unchanged.

LAYER 0 (built): run-to-run dedup memory. `admit()` below is the idempotent core of
the admission gate — it consults the SeenIndex (what the KB already holds) and the
admission ledger (what a prior run already decided) BEFORE evaluating a candidate, so
re-running never re-admits a document already in the KB and never re-judges one a
prior run quarantined. It needs no network and no embeddings, so it is fully tested
(test_dedup.py) ahead of the fetchers. The network `_harvest()` and the Voyage/pgvector
semantic dedup (Layer 2) remain stubs; `admit()` works on any candidate list.
"""
import json
import os
import re
from pathlib import Path

import dedup
import ledger
from fault_lines import FAULT_LINES
from score import _attributes_to, load_feed, load_corpus, FEED_PATH, HARVESTED_PATH

# Admission thresholds (tune against a labeled sample before trusting).
REL_MIN = 0.62       # min cosine to a fault-line centroid to count as relevant (Layer 2)
DEDUP_MAX = 0.94     # >= this cosine to an existing item == near-duplicate (Layer 2)

# Domain -> tier allowlist. Extend deliberately; unknown domains are quarantined.
SOURCE_ALLOWLIST = {
    "courtlistener.com": "T1", "eur-lex.europa.eu": "T1", "federalregister.gov": "T1",
    "leg.colorado.gov": "T1",
    "americanbar.org": "T2", "law.cornell.edu": "T2",
    "law.stanford.edu": "T3", "hai.stanford.edu": "T3",
    "lawnext.com": "T4", "artificiallawyer.com": "T4",
}

VENDOR_DOMAINS = {"harvey.ai", "eudia.com", "legora.com"}  # -> conflict=True

# --- AI-context gate (harvested items only) ---------------------------------
# The fault lines' `signals` are often generic legal words ("disclosure",
# "verification", "competence"), so signal-substring matching alone admits a discovery
# dispute that merely contains the word "disclosure" and quarantines a "Harvey raises
# $550M" post that has no literal signal word. The radar is about AI in legal work, so a
# harvested item must be ABOUT AI to earn admission: signal match AND an AI-context term.
# Matched with word boundaries on normalized text so "ai" does not fire inside "said".
# This is a hard gate for uncurated rows; curated rows (a human attributed them) are exempt.
AI_CONTEXT_PHRASES = (
    "artificial intelligence", "generative ai", "gen ai", "large language model",
    "machine learning", "legal ai", "legal tech", "legal technology", "law tech",
    "legaltech", "lawtech", "legal automation", "ai tool", "ai tools", "ai model",
    "ai use", "ai-assisted", "ai assisted", "ai generated", "ai-generated",
    "ai hallucination", "hallucinated citation", "hallucinated case",
    "chatgpt", "chat gpt", "gpt-4", "copilot", "agentic ai", "autonomous agent",
    "ai agent", "ai act", "deep learning",
)
AI_CONTEXT_TOKENS = ("llm", "llms", "genai", "gpt", "chatgpt", "copilot", "openai", "claude")
# NOTE: the bare token "ai" is deliberately absent — on FULL opinion text it false-fires
# (Hawaiian words, "A.I." abbreviations, etc.). "AI" is still caught when part of a
# specific phrase ("generative AI", "legal AI", "AI tool", ...) in AI_CONTEXT_PHRASES.


def _has_ai_context(item):
    """True if title+text is about AI, matched on word boundaries (so 'ai' doesn't hit
    'said'/'claim'). Deterministic; used to gate harvested (uncurated) admission."""
    text = f"{item.get('title', '')} {item.get('text', '')}"
    norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    padded = f" {norm} "
    if any(f" {p} " in padded for p in AI_CONTEXT_PHRASES):
        return True
    return bool(set(norm.split()) & set(AI_CONTEXT_TOKENS))

# Feed schema keys an admitted row carries (the scorer reads these).
_FEED_KEYS = ("date", "tier", "title", "source", "url", "text",
              "fault_lines", "empirical", "conflict")


def embed_voyage(texts, model="voyage-law-2"):
    """Embed with Voyage's legal model. Requires VOYAGE_API_KEY. Stub until wired (Layer 2)."""
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY not set — ingestion embedding disabled")
    import voyageai  # lazy import so v1 has zero extra deps
    client = voyageai.Client(api_key=api_key)
    return client.embed(texts, model=model, input_type="document").embeddings


def _assign_tier(candidate):
    """Tier from an explicit candidate tier, else the domain allowlist, else None
    (unknown source -> quarantine)."""
    if candidate.get("tier"):
        return candidate["tier"]
    return SOURCE_ALLOWLIST.get(dedup.domain_of(candidate.get("url", "")))


def _relevant_fault_lines(candidate):
    """Layer-0 relevance: which fault lines this candidate matches.

    A curated candidate (a human already attributed `fault_lines`) passes through as-is.
    An uncurated harvested candidate must ALSO be about AI (`_has_ai_context`) — otherwise
    a generic legal word like "disclosure" admits an unrelated discovery dispute. Signal
    match + AI-context is the gate; embedding-cosine relevance remains Layer 2."""
    if candidate.get("fault_lines"):
        return [fl["id"] for fl in FAULT_LINES if _attributes_to(candidate, fl)]
    if not _has_ai_context(candidate):
        return []
    return [fl["id"] for fl in FAULT_LINES if _attributes_to(candidate, fl)]


def _feed_row(candidate, tier, fault_line_ids):
    row = {k: candidate.get(k) for k in _FEED_KEYS if k in candidate}
    row["tier"] = tier
    row["fault_lines"] = fault_line_ids
    row["harvested"] = True   # provenance: machine-fetched, not hand-curated
    row["empirical"] = bool(candidate.get("empirical"))
    conflict = bool(candidate.get("conflict")) or \
        dedup.domain_of(candidate.get("url", "")) in VENDOR_DOMAINS
    row["conflict"] = conflict
    # carry through any optional lane classes the candidate already declares
    for k in ("capability", "market", "enable", "software", "flag", "order",
              "negative_fault_lines", "single_source", "ruling"):
        if k in candidate:
            row[k] = candidate[k]
    return row


def _append_feed(row, feed_path):
    with open(feed_path, "a") as f:
        f.write(json.dumps(row) + "\n")


def admit(candidates, feed_path=HARVESTED_PATH, run=None, dry_run=False, seen_feed=None):
    """Idempotent admission gate. Returns a summary dict; appends admitted rows to the
    HARVESTED store (unless dry_run) and records every decision to the admission ledger.
    The seen-index is built from the FULL corpus (curated + harvested) so a fetched doc
    that duplicates a curated one is caught too.

    Order of checks — cheapest and most memory-driven first:
      1. seen in KB      — canonical URL / content hash / citation echo already held
      2. already decided — a prior run judged this document (skip, don't re-record)
      3. tier gate       — unknown source -> quarantine (kept out, logged)
      4. relevance       — matches no fault line -> quarantine
      5. admit           — append to feed, add to the live SeenIndex, log
    """
    run = run or ledger.run_id()
    # Seen-index over the whole corpus (curated + harvested), not just the target file —
    # a fetched doc duplicating a curated one must be caught as well. `seen_feed` lets
    # callers/tests inject the corpus explicitly.
    seen = ledger.SeenIndex(feed=seen_feed if seen_feed is not None else load_corpus())
    decided = ledger.decided_keys()      # what any prior run already judged
    summary = {"run": run, "n_candidates": len(candidates), "admitted": 0,
               "skipped_in_kb": 0, "skipped_decided": 0, "quarantined": 0,
               "dry_run": bool(dry_run),
               "admitted_titles": [], "decisions": []}

    def _decide(cand, decision, reason, scores=None):
        """Record a decision on the real path, or collect it for preview on a dry run.
        dry_run must have NO side effects — otherwise a preview would poison the ledger
        and the real run would then skip these docs as 'already decided'."""
        row = {"title": cand.get("title", ""), "url": cand.get("url", ""),
               "decision": decision, "reason": reason, "scores": scores or {}}
        summary["decisions"].append(row)
        if not dry_run:
            ledger.record_decision(cand, decision, reason, run=run, scores=scores)
        return row

    for cand in candidates:
        # 2 first for candidates a prior run judged but that are NOT in the KB
        # (e.g. quarantined) — skip silently, no duplicate ledger row.
        if ledger.already_decided(cand, decided):
            summary["skipped_decided"] += 1
            _decide(cand, "skip", "already_decided")
            continue
        # 1 — already in the KB
        reason = seen.seen(cand)
        if reason:
            _decide(cand, "dedup", reason)
            summary["skipped_in_kb"] += 1
            continue
        # 3 — tier gate
        tier = _assign_tier(cand)
        if not tier:
            _decide(cand, "quarantine", "unknown_source",
                    {"domain": dedup.domain_of(cand.get("url", ""))})
            summary["quarantined"] += 1
            continue
        # 4 — relevance
        fls = _relevant_fault_lines(cand)
        if not fls:
            _decide(cand, "quarantine", "no_fault_line_match", {"tier": tier})
            summary["quarantined"] += 1
            continue
        # 5 — admit
        row = _feed_row(cand, tier, fls)
        if not dry_run:
            _append_feed(row, feed_path)
        seen.add(row)   # so a duplicate later in THIS batch is caught too
        _decide(row, "admit", "passed_gate", {"tier": tier, "fault_lines": fls})
        summary["admitted"] += 1
        summary["admitted_titles"].append(row.get("title", ""))

    return summary


def reconcile_kb(feed_path=FEED_PATH):
    """Always-on dedup pass — runs on EVERY radar pass, with or without harvesting.

    This is what makes the run-to-run memory part of the OS rather than an opt-in: on
    every build we rebuild the SeenIndex over the KB and check the KB against itself,
    so a duplicate that ever slips in (a hand-added echo, a double-append) is detected
    and logged, and the seen-memory is guaranteed current before any admission runs.
    Read-only: it reports duplicates, it does not rewrite the curated feed.
    """
    feed = load_corpus(curated=feed_path if feed_path else FEED_PATH)
    index = ledger.SeenIndex(feed=[])
    duplicates = []   # true content duplicates — a real integrity problem
    shared = []       # same URL / citation but distinct content — informational
    for item in feed:
        reason = index.seen(item)
        rec = {"title": item.get("title", ""), "url": item.get("url", ""), "reason": reason}
        if reason == "content_in_kb":
            duplicates.append(rec)
        elif reason:
            shared.append(rec)
        index.add(item)
    return {"n_items": len(feed), "n_unique_urls": len(index.urls),
            "n_duplicates": len(duplicates), "duplicates": duplicates,
            "n_shared_source": len(shared), "shared_source": shared}


def _harvest(live=None):
    """Fetch candidate docs from the allowlisted sources (see fetchers.py). Offline by
    default — returns [] and makes no network calls unless live is set (or
    RADAR_LIVE_FETCH=1)."""
    import fetchers
    return fetchers.harvest(live=live)


def harvest_and_admit(feed_path=HARVESTED_PATH, live=None, dry_run=False):
    """harvest -> admit. Returns the admit() summary dict (with `live` folded in).
    dry_run=True previews decisions and writes nothing (no feed append, no ledger row)."""
    import fetchers
    is_live = live if live is not None else (os.environ.get("RADAR_LIVE_FETCH") == "1")
    summary = admit(_harvest(live=live), feed_path=feed_path, dry_run=dry_run)
    summary["live"] = bool(is_live)
    summary["sources_allowlisted"] = len(fetchers.SOURCES)
    return summary
