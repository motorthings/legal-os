"""Tests for the Layer-2 embedding gate — pure functions + mocked gate, no network.

Proves: cosine similarity math, best-match sorting, the semantic gate mapping candidates
to fault lines by cosine (with a mocked embedder), and the no-key fallback to None.
"""
import sys
from pathlib import Path

RADAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADAR))

import embed
import ingest


def test_cosine():
    assert abs(embed.cosine([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9
    assert abs(embed.cosine([1, 0, 0], [0, 1, 0]) - 0.0) < 1e-9
    assert embed.cosine([0, 0], [0, 0]) == 0.0   # zero-vector guard
    assert abs(embed.cosine([1, 1], [1, 1]) - 1.0) < 1e-9


def test_best_match_sorts_desc():
    centroids = {"a": [1, 0], "b": [0, 1], "c": [1, 1]}
    top = embed.best_match([1, 0.1], centroids)
    assert top[0][0] == "a"          # most similar to [1,0]
    assert top[-1][0] == "b"         # least similar


def test_build_gate_maps_by_cosine():
    orig_client = embed._make_client
    orig_centroids = embed.get_centroids
    orig_embed = embed.embed
    try:
        embed._make_client = lambda: object()
        embed.get_centroids = lambda client=None: {
            "disclosure": [1.0, 0.0],
            "verification": [0.0, 1.0],
        }
        def fake_embed(texts, client=None):
            out = []
            for t in texts:
                if "disclosure" in t:
                    out.append([1.0, 0.0])
                elif "verification" in t:
                    out.append([0.0, 1.0])
                else:
                    out.append([0.0, 0.0])
            return out
        embed.embed = fake_embed
        cands = [
            {"title": "a disclosure case", "text": "disclosure of AI use"},
            {"title": "a verification case", "text": "verification duty"},
        ]
        gate = embed.build_gate(cands, rel_min=0.6)
        assert gate is not None
        assert gate(cands[0]) == ["disclosure"]
        assert gate(cands[1]) == ["verification"]
    finally:
        embed._make_client = orig_client
        embed.get_centroids = orig_centroids
        embed.embed = orig_embed


def test_gate_none_without_key():
    orig_client = embed._make_client
    try:
        embed._make_client = lambda: None   # simulate no VOYAGE_API_KEY
        assert embed.build_gate([{"title": "x", "text": "y"}]) is None
        # and _relevant_fault_lines falls back to keyword matching (no crash)
        c = {"title": "AI disclosure", "text": "disclosure of artificial intelligence"}
        assert ingest._relevant_fault_lines(c, gate=None) == ["disclosure"]
    finally:
        embed._make_client = orig_client


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {t.__name__}")
            import traceback; traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
