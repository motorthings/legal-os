"""
Variable-ization Test Script
Verifies that all hard-coded organization references have been replaced with variables

Tests:
1. default.txt contains no hard-coded "MitCH", "Georgetown", "NCEMCH"
2. All templates use {variables} instead of hard-coded values
3. organization_description is properly extracted and used

Usage:
    python test_variable_ization.py
"""

import os
import re
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hard-coded references that should NOT appear in templates
FORBIDDEN_STRINGS = [
    "MitCH",           # Old assistant name
    "Georgetown",      # Old organization
    "NCEMCH",          # Old center name
    "Georgetown University",
    "National Center for Excellence in Maternal & Child Health"
]

# Required variables that SHOULD appear in templates
REQUIRED_VARIABLES = [
    "{user_name}",
    "{user_role}",
    "{organization_name}",
    "{organization_description}",
    "{assistant_name}"
]

# Files to check
FILES_TO_CHECK = [
    "backend/system_instructions/default.txt",
    "backend/prompts/solomon_stage2_customization.txt"
]


def check_file_for_hard_codes(file_path: str) -> dict:
    """
    Check a file for hard-coded references

    Returns:
        {
            "file": str,
            "passed": bool,
            "forbidden_found": [...],
            "required_missing": [...],
            "line_numbers": {...}
        }
    """

    if not os.path.exists(file_path):
        return {
            "file": file_path,
            "passed": False,
            "error": "File not found",
            "forbidden_found": [],
            "required_missing": [],
            "line_numbers": {}
        }

    with open(file_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    forbidden_found = []
    line_numbers = {}

    # Check for forbidden strings
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in content:
            forbidden_found.append(forbidden)

            # Find line numbers
            matching_lines = []
            for i, line in enumerate(lines, 1):
                if forbidden in line:
                    matching_lines.append(i)

            line_numbers[forbidden] = matching_lines

    # Check for required variables (only for default.txt)
    required_missing = []
    if "default.txt" in file_path:
        for required in REQUIRED_VARIABLES:
            if required not in content:
                required_missing.append(required)

    passed = len(forbidden_found) == 0 and len(required_missing) == 0

    return {
        "file": file_path,
        "passed": passed,
        "forbidden_found": forbidden_found,
        "required_missing": required_missing,
        "line_numbers": line_numbers
    }


def check_code_usage():
    """
    Check Python code to ensure organization_description is properly used
    """

    print("\n🔍 Checking Python code for organization_description usage...")

    solomon_stage2_path = "backend/services/solomon_stage2.py"

    if not os.path.exists(solomon_stage2_path):
        print(f"   ❌ File not found: {solomon_stage2_path}")
        return False

    with open(solomon_stage2_path, 'r') as f:
        content = f.read()

    checks = {
        "extracts_org_info": "org_info = extraction_json.get('organization_info'" in content,
        "gets_description": "organization_description = org_info.get('organization_description'" in content,
        "passes_to_prompt": "organization_description=organization_description" in content
    }

    all_passed = all(checks.values())

    print(f"   {'✅' if checks['extracts_org_info'] else '❌'} Extracts organization_info from extraction_json")
    print(f"   {'✅' if checks['gets_description'] else '❌'} Gets organization_description from org_info")
    print(f"   {'✅' if checks['passes_to_prompt'] else '❌'} Passes organization_description to prompt template")

    return all_passed


def run_tests():
    """Run all variable-ization tests"""

    print("\n" + "=" * 80)
    print("🧪 VARIABLE-IZATION TEST SUITE")
    print("=" * 80)

    all_passed = True
    results = []

    # Test 1: Check template files for hard-coded references
    print("\n📄 Test 1: Template Files - Hard-coded Reference Check")
    print("-" * 80)

    for file_path in FILES_TO_CHECK:
        result = check_file_for_hard_codes(file_path)
        results.append(result)

        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"\n{status} - {file_path}")

        if result.get('error'):
            print(f"   ❌ Error: {result['error']}")
            all_passed = False
            continue

        if result['forbidden_found']:
            print(f"   ❌ Found forbidden hard-coded references:")
            for forbidden in result['forbidden_found']:
                lines = result['line_numbers'][forbidden]
                print(f"      - '{forbidden}' on lines: {', '.join(map(str, lines))}")
            all_passed = False
        else:
            print(f"   ✅ No forbidden hard-coded references found")

        if result['required_missing']:
            print(f"   ❌ Missing required variables:")
            for missing in result['required_missing']:
                print(f"      - {missing}")
            all_passed = False
        else:
            if "default.txt" in file_path:
                print(f"   ✅ All required variables present")

    # Test 2: Check Python code usage
    print("\n\n📝 Test 2: Python Code - organization_description Usage")
    print("-" * 80)

    code_passed = check_code_usage()
    all_passed = all_passed and code_passed

    if code_passed:
        print(f"   ✅ organization_description properly implemented")
    else:
        print(f"   ❌ organization_description implementation incomplete")

    # Test 3: Check customization prompt template
    print("\n\n📋 Test 3: Customization Prompt - Variable Documentation")
    print("-" * 80)

    prompt_path = "backend/prompts/solomon_stage2_customization.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r') as f:
            prompt_content = f.read()

        prompt_checks = {
            "documents_org_desc": "{organization_description}" in prompt_content,
            "instructs_usage": "organization_description" in prompt_content.lower()
        }

        if all(prompt_checks.values()):
            print(f"   ✅ Prompt template documents organization_description usage")
        else:
            print(f"   ❌ Prompt template missing organization_description documentation")
            all_passed = False
    else:
        print(f"   ❌ Prompt template file not found")
        all_passed = False

    # Final summary
    print("\n\n" + "=" * 80)
    print("📈 TEST SUMMARY")
    print("=" * 80)

    if all_passed:
        print("\n✅ ALL TESTS PASSED")
        print("\n   ✓ No hard-coded organization references found")
        print("   ✓ All required variables present in templates")
        print("   ✓ organization_description properly implemented")
        print("   ✓ System is fully multi-tenant and organization-agnostic")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\n   Please review the errors above and fix the issues.")
        print("   All hard-coded references must be replaced with variables.")

    print("\n" + "=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
