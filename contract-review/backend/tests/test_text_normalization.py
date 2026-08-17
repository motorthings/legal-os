"""Tests for text_normalization — the deterministic NLP preprocessing layer.

Standalone: imports only the module under test, no config/conftest dependency,
so it can run against the repo as currently committed (where ``config.constants``
does not exist).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_normalization import (
    find_last_sentence_boundary,
    normalize_text,
    split_sentences,
)


# --- segmentation: abbreviations and references do not split sentences ---

def test_abbreviations_do_not_split():
    text = "Acme Corp. and Beta Inc. shall indemnify the Company. This ends here."
    sents = split_sentences(text)
    assert sents == [
        "Acme Corp. and Beta Inc. shall indemnify the Company.",
        "This ends here.",
    ]


def test_section_reference_does_not_split():
    text = "See §4.2(a)(ii) for the governing terms. That is all."
    sents = split_sentences(text)
    assert len(sents) == 2
    assert sents[0] == "See §4.2(a)(ii) for the governing terms."


def test_decimal_does_not_split():
    text = "The fee is $1,250,000.00 USD per year. No exceptions."
    sents = split_sentences(text)
    assert len(sents) == 2
    assert sents[0] == "The fee is $1,250,000.00 USD per year."


def test_multidot_jurisdiction_does_not_split():
    text = "Governing law is the U.S. Federal Rules. End."
    sents = split_sentences(text)
    assert sents == ["Governing law is the U.S. Federal Rules.", "End."]


def test_initial_does_not_split():
    text = "Signed by John A. Smith. Done."
    sents = split_sentences(text)
    assert sents == ["Signed by John A. Smith.", "Done."]


def test_dates_are_one_sentence():
    text = "Effective as of December 3, 2026. Term ends."
    sents = split_sentences(text)
    assert len(sents) == 2
    assert sents[0] == "Effective as of December 3, 2026."


# --- chunk boundary: never lands mid-reference ---

def test_boundary_does_not_land_on_section_ref():
    window = (
        "The Parties agree to the terms set forth in Section 4.2(a)(ii) and "
        "further agree that this is a long clause which continues at length. "
        "The next sentence follows here."
    )
    boundary = find_last_sentence_boundary(window, threshold=0.5)
    assert boundary is not None
    # The boundary must be at the true sentence end, not right after "4.2".
    assert window[boundary - 1] == "."
    assert "4.2(a)(ii)" in window[:boundary]


def test_boundary_none_when_window_too_short():
    window = "Acme Corp. and Beta Inc. shall indemnify the Company"
    assert find_last_sentence_boundary(window, threshold=0.5) is None


# --- normalization: page artifacts and whitespace removed ---

def test_page_markers_stripped():
    text = "=== Page 1 ===\nThe Parties agree.\n=== Page 2 ===\nThe term is two years."
    out = normalize_text(text)
    assert "Page" not in out
    assert "===" not in out
    assert "The Parties agree." in out


def test_whitespace_collapsed_and_nbsp_normalized():
    text = "The  Parties agree\tto\r\nterms."
    out = normalize_text(text)
    assert "  " not in out
    assert " " not in out
    assert "\t" not in out


def test_repeated_header_deduped():
    text = (
        "CONFIDENTIAL\n"
        "Section 1. Payment.\n"
        "CONFIDENTIAL\n"
        "Section 2. Term.\n"
        "CONFIDENTIAL\n"
    )
    out = normalize_text(text)
    assert out.count("CONFIDENTIAL") == 1
    assert "Section 1." in out
    assert "Section 2." in out


def test_lowercase_flag():
    assert normalize_text("Hello World", lowercase=True) == "hello world"
    assert normalize_text("Hello World") == "Hello World"


def test_empty_input():
    assert normalize_text("") == ""
    assert split_sentences("") == []


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failures += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    sys.exit(1 if failures else 0)
