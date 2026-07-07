#!/usr/bin/env python3
"""
Improved Text Validation for Document Processing

This module provides enhanced validation to detect corrupted .docx XML,
binary data, and other non-readable content that passes simple printable ratio tests.

The improved validation catches:
1. ZIP file headers (PK magic bytes)
2. Excessive XML tags (indicates .docx internals)
3. Very low word density (gibberish vs natural language)
4. Binary patterns that look printable
"""

import re
from typing import Tuple


def is_valid_text_content_improved(
    text: str,
    min_printable_ratio: float = 0.70,
    max_xml_ratio: float = 0.30,
    min_word_density: float = 0.10
) -> Tuple[bool, str]:
    """
    Enhanced validation that text content is readable, not corrupted.

    Args:
        text: Text to validate
        min_printable_ratio: Minimum ratio of printable characters (default 70%)
        max_xml_ratio: Maximum ratio of XML tag characters (default 30%)
        min_word_density: Minimum ratio of alphabetic words (default 10%)

    Returns:
        Tuple of (is_valid, reason)
        - is_valid: True if text appears valid, False if corrupted
        - reason: Explanation if invalid
    """

    # Check 1: Empty or whitespace only
    if not text or len(text.strip()) == 0:
        return False, "Empty or whitespace-only content"

    # Check 2: ZIP file header (corrupted .docx)
    if text.startswith('PK'):
        return False, "ZIP file header detected (corrupted .docx export)"

    # Check 3: Printable ratio (catch obvious binary)
    printable_count = sum(1 for c in text if c.isprintable() or c.isspace())
    printable_ratio = printable_count / len(text) if len(text) > 0 else 0

    if printable_ratio < min_printable_ratio:
        return False, f"Low printable ratio ({printable_ratio:.1%} < {min_printable_ratio:.1%})"

    # Check 4: Excessive XML tags (.docx XML internals)
    # Count characters that are part of XML tags
    xml_pattern = r'<[^>]+>'
    xml_chars = sum(len(match.group()) for match in re.finditer(xml_pattern, text))
    xml_ratio = xml_chars / len(text) if len(text) > 0 else 0

    if xml_ratio > max_xml_ratio:
        return False, f"Excessive XML tags ({xml_ratio:.1%} > {max_xml_ratio:.1%}) - likely .docx internals"

    # Check 5: Word density (natural language check)
    # Count sequences of 2+ alphabetic characters (words)
    words = re.findall(r'[a-zA-Z]{2,}', text)
    word_chars = sum(len(word) for word in words)
    word_density = word_chars / len(text) if len(text) > 0 else 0

    if word_density < min_word_density:
        return False, f"Low word density ({word_density:.1%} < {min_word_density:.1%}) - not natural language"

    # Check 6: Suspicious patterns (common in corrupted files)
    suspicious_patterns = [
        r'PK\x03\x04',  # ZIP header
        r'word/document\.xml',  # .docx internals
        r'word/numbering\.xml',  # .docx internals
        r'\x00{5,}',  # Null byte sequences
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, text):
            return False, f"Suspicious pattern detected: {pattern}"

    # All checks passed
    return True, "Valid text content"


def test_validation():
    """Test the improved validation with various inputs."""

    test_cases = [
        # (text, expected_valid, description)
        ("This is normal readable text about rabbits.", True, "Normal text"),
        ("PK|s[word/numbering.xmlKn0O; !FElXu...", False, "Corrupted .docx XML"),
        ("<word><document><numbering>...</numbering></document></word>" * 100, False, "Excessive XML"),
        ("aB3!@#xYz9876qwerty", False, "Low word density gibberish"),
        ("The quick brown fox jumps over the lazy dog. " * 10, True, "Repeated natural language"),
        ("", False, "Empty string"),
        ("   \n\t  ", False, "Whitespace only"),
    ]

    print("\n" + "="*80)
    print("VALIDATION TEST RESULTS")
    print("="*80 + "\n")

    for text, expected_valid, description in test_cases:
        is_valid, reason = is_valid_text_content_improved(text)
        status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"

        print(f"{status} | {description}")
        print(f"     Expected: {expected_valid}, Got: {is_valid}")
        print(f"     Reason: {reason}")
        print(f"     Text preview: {text[:60]}...")
        print()


# Drop-in replacement for google_drive_sync.py
def is_valid_text_content(text: str, min_printable_ratio: float = 0.70) -> bool:
    """
    Drop-in replacement for the existing validation function.
    Returns only boolean for backwards compatibility.
    """
    is_valid, _ = is_valid_text_content_improved(text, min_printable_ratio)
    return is_valid


if __name__ == "__main__":
    test_validation()
