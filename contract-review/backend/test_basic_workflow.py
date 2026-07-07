#!/usr/bin/env python3
"""
Basic Workflow Test - Simple functionality verification
No performance metrics, just "does it work?"
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_section(title):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{title:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def test_check(name, passed, message=""):
    icon = "✅" if passed else "❌"
    color = GREEN if passed else RED
    print(f"{icon} {BOLD}{name}{RESET}: {color}{'PASS' if passed else 'FAIL'}{RESET}")
    if message:
        print(f"   {message}")
    return passed

def test_environment():
    """Check if basic environment is set up"""
    print_section("Environment Check")

    required = ['SUPABASE_URL', 'ANTHROPIC_API_KEY', 'VOYAGE_API_KEY']
    all_good = True

    for var in required:
        exists = bool(os.getenv(var))
        test_check(var, exists, f"{'Present' if exists else 'MISSING - set this in .env'}")
        if not exists:
            all_good = False

    return all_good

def test_files_exist():
    """Check if key system files exist"""
    print_section("System Files Check")

    files = {
        'Baseline Library': 'system_instructions/library_baseline.xml',
        'System Instructions': 'system_instructions/default.txt',
        'Solomon Stage 1': 'services/solomon_stage1.py',
        'Solomon Stage 2': 'services/solomon_stage2.py',
        'Voice Interview Script': '../docs/voice-interview/Voice_Interview_Script_for_Paige_Review.md'
    }

    all_good = True
    for name, path in files.items():
        full_path = os.path.join(os.path.dirname(__file__), path)
        exists = os.path.exists(full_path)
        test_check(name, exists, f"Path: {path}")
        if not exists:
            all_good = False

    return all_good

def test_de_mitching():
    """Verify Georgetown references removed"""
    print_section("De-Mitching Verification")

    try:
        with open('system_instructions/default.txt', 'r') as f:
            content = f.read()

        # Bad terms that should NOT exist
        bad_terms = ['Georgetown', 'NCEMCH']
        found_bad = []
        for term in bad_terms:
            if term in content:
                found_bad.append(term)

        # Good terms that SHOULD exist
        good_terms = ['{organization_name}', '{user_name}']
        found_good = []
        for term in good_terms:
            if term in content:
                found_good.append(term)

        if found_bad:
            test_check("No Hard-coded References", False, f"Found: {', '.join(found_bad)}")
            return False
        else:
            test_check("No Hard-coded References", True, "Georgetown/NCEMCH removed ✓")

        if len(found_good) >= 1:
            test_check("Variables Present", True, f"Found: {', '.join(found_good)}")
            return True
        else:
            test_check("Variables Present", False, "No template variables found")
            return False

    except Exception as e:
        test_check("De-Mitching Check", False, str(e))
        return False

def test_library_functions():
    """Check if baseline library has 5 core functions"""
    print_section("Baseline Library Check")

    try:
        with open('system_instructions/library_baseline.xml', 'r') as f:
            content = f.read()

        functions = [
            'Conceptual_Modeler',
            'Independence_Identifier',
            'Report_Builder',
            'Feedback_Drafter',
            'Signal_Analyzer'
        ]

        found = []
        for func in functions:
            if f'name="{func}"' in content or f"name='{func}'" in content:
                found.append(func)

        if len(found) >= 5:
            test_check("5 Core Functions", True, f"Found all 5 baseline functions")
            return True
        else:
            test_check("5 Core Functions", False, f"Only found {len(found)}: {', '.join(found)}")
            return False

    except Exception as e:
        test_check("Library Check", False, str(e))
        return False

def test_backend_running():
    """Check if backend is accessible"""
    print_section("Backend Status")

    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=3)

        if response.status_code == 200:
            test_check("Backend Health", True, "Backend is running on port 8000")
            return True
        else:
            test_check("Backend Health", False, f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        test_check("Backend Health", False, "Backend not running - start it first")
        return False
    except Exception as e:
        test_check("Backend Health", False, str(e))
        return False

def test_database_connection():
    """Check if database is accessible"""
    print_section("Database Connection")

    try:
        from database import get_supabase
        supabase = get_supabase()

        # Try simple query
        response = supabase.table('users').select('id').limit(1).execute()

        test_check("Database", True, "Connected to Supabase")
        return True
    except Exception as e:
        test_check("Database", False, str(e))
        return False

def test_ai_services():
    """Quick test of AI services"""
    print_section("AI Services")

    # Test Claude
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )

        test_check("Claude API", True, "Connected to Anthropic")
    except Exception as e:
        test_check("Claude API", False, str(e)[:50])
        return False

    # Test Voyage
    try:
        import voyageai
        client = voyageai.Client(api_key=os.getenv('VOYAGE_API_KEY'))

        result = client.embed(["test"], model="voyage-3")

        test_check("Voyage AI", True, "Embedding service working")
    except Exception as e:
        test_check("Voyage AI", False, str(e)[:50])
        return False

    return True

def main():
    print(f"\n{BOLD}{BLUE}SuperAssistant Basic Workflow Test{RESET}")
    print(f"Testing basic functionality for demo\n")

    results = []

    # Run tests
    results.append(("Environment", test_environment()))
    results.append(("System Files", test_files_exist()))
    results.append(("De-Mitching", test_de_mitching()))
    results.append(("Baseline Library", test_library_functions()))
    results.append(("Backend", test_backend_running()))
    results.append(("Database", test_database_connection()))
    results.append(("AI Services", test_ai_services()))

    # Summary
    print_section("Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")

    print(f"\n{BOLD}Result: {passed}/{total} checks passed{RESET}\n")

    if passed == total:
        print(f"{GREEN}{BOLD}🎉 All systems operational! Ready for demo.{RESET}\n")
        return 0
    elif passed >= total - 2:
        print(f"{YELLOW}{BOLD}⚠️  Mostly ready. Review failures above.{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}❌ Multiple issues found. Fix before demo.{RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
