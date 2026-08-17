"""
Legal AI OS — Legal Research Unit Tests

Pure-logic tests for the Descrybe service and matter enrichment.
No database or network required.
"""

import pytest

from app.services.descrybe import DescrybeClient, ResearchResult
from app.services.matter_enrichment import _build_queries


# ---------------------------------------------------------------------------
# Matter enrichment — query building
# ---------------------------------------------------------------------------
class TestBuildQueries:
    def test_builds_concept_and_law_queries_from_practice_area(self):
        matter = {
            "jurisdiction": "US",
            "practice_area": "employment",
            "name": "Wrongful termination claim",
            "description": "",
            "adverse_parties": [],
        }
        queries = _build_queries(matter)
        types = [q["query_type"] for q in queries]

        assert "concept_search" in types
        assert "law_search" in types

        concept = next(q for q in queries if q["query_type"] == "concept_search")
        assert "employment" in concept["query_text"]
        assert concept["jurisdiction"] == "US"

    def test_builds_citation_lookup_from_adverse_parties(self):
        matter = {
            "jurisdiction": "US-CA",
            "practice_area": "litigation",
            "name": "Smith v. Jones",
            "description": "",
            "adverse_parties": ["Acme Corp", "Beta LLC"],
        }
        queries = _build_queries(matter)
        types = [q["query_type"] for q in queries]

        assert "citation_lookup" in types
        citations = [q for q in queries if q["query_type"] == "citation_lookup"]
        assert len(citations) == 2

    def test_empty_matter_returns_no_queries(self):
        matter = {
            "jurisdiction": None,
            "practice_area": None,
            "name": "",
            "description": "",
            "adverse_parties": [],
        }
        assert _build_queries(matter) == []

    def test_description_fallback_when_no_practice_area(self):
        matter = {
            "jurisdiction": "US",
            "practice_area": "",
            "name": "",
            "description": "Client is being sued for breach of contract.",
            "adverse_parties": [],
        }
        queries = _build_queries(matter)
        assert len(queries) == 1
        assert queries[0]["query_type"] == "concept_search"
        assert "breach of contract" in queries[0]["query_text"]


# ---------------------------------------------------------------------------
# Descrybe result normalization
# ---------------------------------------------------------------------------
def _client_without_init() -> DescrybeClient:
    return object.__new__(DescrybeClient)


class TestNormalizeCaseSearch:
    def test_normalizes_standard_results(self):
        client = _client_without_init()
        raw = {
            "results": [
                {
                    "case_id": "c931121",
                    "title": "University of Tex. Southwestern Medical Center v. Nassar",
                    "citation": "133 S. Ct. 2517",
                    "state": "Federal Supreme Court",
                    "court": "Supreme Court of the United States",
                    "decision_date": "2013-06-24",
                    "body": "Retaliation is recognized as a form of discrimination...",
                    "why_relevant": "Matches the likely issue: Retaliation Claims under Title VII.",
                    "treatment": {"indicator": "positive", "weight": "binding", "category": "followed"},
                    "research_value": {"label": "Leading authority", "note": "..."},
                    "url": "https://descrybe.com/share/case-viewer/c931121/...",
                }
            ]
        }
        results = client._normalize_case_search(raw)
        assert len(results) == 1
        r = results[0]
        assert r.case_id == "c931121"
        assert r.title == "University of Tex. Southwestern Medical Center v. Nassar"
        assert r.citation == "133 S. Ct. 2517"
        assert r.jurisdiction == "Federal Supreme Court"
        assert r.decision_year == 2013
        assert r.treatment == "positive"
        assert r.is_good_law is True
        assert r.authority_label == "Leading authority"
        assert r.source_url.startswith("https://descrybe.com")

    def test_maps_negative_treatment_to_bad_law(self):
        client = _client_without_init()
        raw = {
            "results": [
                {
                    "case_id": "c744598",
                    "title": "Robinson v. City of Pittsburgh",
                    "decision_date": "1997-07-14",
                    "treatment": {"indicator": "negative", "category": "overruled"},
                }
            ]
        }
        results = client._normalize_case_search(raw)
        assert results[0].treatment == "negative"
        assert results[0].is_good_law is False

    def test_maps_unknown_treatment_to_none(self):
        client = _client_without_init()
        raw = {
            "results": [
                {
                    "case_id": "c4498055",
                    "title": "Fassbender v. Correct Care Solutions",
                    "treatment": {"indicator": "unknown"},
                }
            ]
        }
        results = client._normalize_case_search(raw)
        assert results[0].is_good_law is None

    def test_handles_empty_results(self):
        client = _client_without_init()
        assert client._normalize_case_search({}) == []

    def test_skips_non_dict_items(self):
        client = _client_without_init()
        raw = {"results": ["not a dict", None, {"case_id": "c1", "title": "A v B"}]}
        results = client._normalize_case_search(raw)
        assert len(results) == 1


class TestNormalizeLawSearch:
    def test_normalizes_law_results(self):
        client = _client_without_init()
        raw = {
            "results": [
                {
                    "id": "17-cfr-240",
                    "citation": "17 CFR § 240.14a-8",
                    "title": "Shareholder Proposals",
                    "jurisdiction": "Federal",
                    "matched_passage": "A company must include...",
                }
            ]
        }
        results = client._normalize_law_search(raw)
        assert len(results) == 1
        assert results[0].citation == "17 CFR § 240.14a-8"
        assert results[0].title == "Shareholder Proposals"


# ---------------------------------------------------------------------------
# Cache key determinism
# ---------------------------------------------------------------------------
class TestCacheKey:
    def test_cache_key_is_deterministic(self):
        client = _client_without_init()
        a = client._cache_key("concept_search", "Discrimination", "US", "employment", {})
        b = client._cache_key("concept_search", "Discrimination", "US", "employment", {})
        assert a == b

    def test_cache_key_varies_with_input(self):
        client = _client_without_init()
        a = client._cache_key("concept_search", "Discrimination", "US", "employment", {})
        b = client._cache_key("concept_search", "Retaliation", "US", "employment", {})
        assert a != b

    def test_cache_key_case_insensitive(self):
        client = _client_without_init()
        a = client._cache_key("concept_search", "Discrimination", "US", "employment", {})
        b = client._cache_key("concept_search", "discrimination", "US", "employment", {})
        assert a == b
