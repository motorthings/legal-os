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
"""
import os

# Admission thresholds (tune against a labeled sample before trusting).
REL_MIN = 0.62       # min cosine to a fault-line centroid to count as relevant
DEDUP_MAX = 0.94     # >= this cosine to an existing item == near-duplicate

# Domain -> tier allowlist. Extend deliberately; unknown domains are quarantined.
SOURCE_ALLOWLIST = {
    "courtlistener.com": "T1", "eur-lex.europa.eu": "T1", "federalregister.gov": "T1",
    "leg.colorado.gov": "T1",
    "americanbar.org": "T2", "law.cornell.edu": "T2",
    "law.stanford.edu": "T3", "hai.stanford.edu": "T3",
    "lawnext.com": "T4", "artificiallawyer.com": "T4",
}

VENDOR_DOMAINS = {"harvey.ai", "eudia.com", "legora.com"}  # -> conflict=True


def embed_voyage(texts, model="voyage-law-2"):
    """Embed with Voyage's legal model. Requires VOYAGE_API_KEY. Stub until wired."""
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY not set — ingestion embedding disabled")
    import voyageai  # lazy import so v1 has zero extra deps
    client = voyageai.Client(api_key=api_key)
    return client.embed(texts, model=model, input_type="document").embeddings


def harvest_and_admit():
    """Run harvest -> admission gate -> index. Returns count admitted.

    Not implemented in v1. Raises so run.py logs 'ingest_skipped' and still builds
    the page from the curated feed. Implement stage by stage; the scorer needs no
    changes because admitted rows use the existing feed schema.
    """
    raise NotImplementedError(
        "Phase 2 harvester not wired yet. v1 scores the curated feed.jsonl. "
        "Implement harvest() -> admit() -> index() against SOURCE_ALLOWLIST."
    )
