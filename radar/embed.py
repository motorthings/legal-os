"""Layer-2 semantic relevance — embedding cosine gate for harvested items.

The keyword relevance gate (AI-context + signal substrings) over-matches full opinion
text: a 127KB opinion contains "artificial intelligence" AND "disclosure"/"training"/
"competence" even when it is not about AI in legal work. The fix is semantic: embed each
fault line's description as a centroid, embed each harvested candidate, and admit only
when the cosine similarity clears REL_MIN.

Centroids are static (they change only when fault_lines.py changes), so they are cached
to disk keyed by a fingerprint of the centroid texts — embedded once, not per run.
Candidate embeddings are batched into a single API call per run.

Offline-safe: every entry point returns None/{} (no gate) when VOYAGE_API_KEY is absent,
so CI and tests stay deterministic and callers fall back to keyword matching.
"""
import hashlib
import json
import math
import os
from pathlib import Path

from fault_lines import FAULT_LINES

CENTROID_FILE = Path(__file__).parent / "history" / "fault_line_centroids.json"
MODEL = "voyage-law-2"


def _make_client():
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        return None
    import voyageai
    return voyageai.Client(api_key=key)


def _centroid_text(fl):
    """The prose that represents a fault line semantically: title + the analyst vector."""
    return f"{fl['title']}. {fl['vector']}"


def _fingerprint():
    blob = "||".join(_centroid_text(fl) for fl in FAULT_LINES)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cosine(a, b):
    """Cosine similarity of two equal-length float vectors. Pure + deterministic."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if (na and nb) else 0.0


def embed(texts, client=None):
    """Embed a list of strings -> list of vectors. Returns [] on any failure (never
    raises — one bad batch must not block the pass)."""
    if client is None:
        client = _make_client()
    if client is None or not texts:
        return []
    try:
        resp = client.embed(texts, model=MODEL, input_type="document")
        return list(resp.embeddings)
    except Exception:
        return []


def load_centroids():
    """Cached {fault_line_id: vector} if fresh (fingerprint matches), else None."""
    if not CENTROID_FILE.exists():
        return None
    try:
        data = json.loads(CENTROID_FILE.read_text())
    except (ValueError, OSError):
        return None
    if data.get("fingerprint") != _fingerprint():
        return None
    return data.get("centroids")


def get_centroids(client=None):
    """Centroids, cached or freshly embedded. {} when embeddings are unavailable."""
    cached = load_centroids()
    if cached:
        return cached
    if client is None:
        client = _make_client()
    if client is None:
        return {}
    texts = [_centroid_text(fl) for fl in FAULT_LINES]
    vecs = embed(texts, client=client)
    if not vecs or len(vecs) != len(FAULT_LINES):
        return {}
    centroids = {fl["id"]: vecs[i] for i, fl in enumerate(FAULT_LINES)}
    data = {"fingerprint": _fingerprint(), "centroids": centroids}
    CENTROID_FILE.parent.mkdir(parents=True, exist_ok=True)
    CENTROID_FILE.write_text(json.dumps(data))
    return centroids


def best_match(vec, centroids):
    """[(fault_line_id, cosine)] sorted highest-similarity first."""
    return sorted(((fid, cosine(vec, c)) for fid, c in centroids.items()),
                  key=lambda x: -x[1])


def build_gate(candidates, rel_min=0.62, client=None):
    """Build a semantic relevance gate over uncurated candidates.

    Returns a callable `candidate -> [fault_line_id, ...]` (cosine >= rel_min), or None
    when embeddings are unavailable (no VOYAGE_API_KEY). Candidates are embedded in one
    batch; the returned gate looks up by the candidate's content hash."""
    if client is None:
        client = _make_client()
    if client is None or not candidates:
        return None
    centroids = get_centroids(client=client)
    if not centroids:
        return None
    from dedup import content_hash
    texts = [f"{c.get('title', '')}. {c.get('text', '')}" for c in candidates]
    vecs = embed(texts, client=client)
    by_hash = {}
    for c, vec in zip(candidates, vecs):
        if not vec:
            continue
        by_hash[content_hash(c)] = [fid for fid, s in best_match(vec, centroids)
                                    if s >= rel_min]

    def gate(candidate):
        return by_hash.get(content_hash(candidate), [])

    return gate
