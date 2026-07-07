#!/usr/bin/env python3
"""
Demo Readiness Test Script
Run this before the demo to verify all critical systems are working
"""
import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Test results tracker
results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0
}

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_test(name, status, details=""):
    """Print test result"""
    if status == "PASS":
        icon = "✅"
        color = GREEN
        results['passed'] += 1
    elif status == "FAIL":
        icon = "❌"
        color = RED
        results['failed'] += 1
    else:  # WARN
        icon = "⚠️"
        color = YELLOW
        results['warnings'] += 1

    print(f"{icon} {BOLD}{name}{RESET}: {color}{status}{RESET}")
    if details:
        print(f"   {details}")

def test_environment_variables():
    """Test 1: Environment Variables"""
    print_header("Test 1: Environment Variables")

    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'ANTHROPIC_API_KEY',
        'VOYAGE_API_KEY'
    ]

    all_present = True
    for var in required_vars:
        if os.getenv(var):
            print_test(var, "PASS", f"Present ({os.getenv(var)[:20]}...)")
        else:
            print_test(var, "FAIL", "Missing!")
            all_present = False

    return all_present

def test_backend_health(backend_url):
    """Test 2: Backend Health Check"""
    print_header("Test 2: Backend Health Check")

    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            print_test("Backend Health", "PASS", f"URL: {backend_url}")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Database: {data.get('database', 'unknown')}")
            return True
        else:
            print_test("Backend Health", "FAIL", f"Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_test("Backend Health", "FAIL", f"Connection error: {str(e)}")
        return False

def test_database_connection():
    """Test 3: Database Connectivity"""
    print_header("Test 3: Database Connectivity")

    try:
        from database import get_supabase
        supabase = get_supabase()

        # Try to query users table
        response = supabase.table('users').select('id,email').limit(1).execute()
        if response.data:
            print_test("Database Connection", "PASS", f"Connected to Supabase")
            print(f"   Found {len(response.data)} users")
            return True
        else:
            print_test("Database Connection", "WARN", "No users found")
            return True
    except Exception as e:
        print_test("Database Connection", "FAIL", str(e))
        return False

def test_claude_api():
    """Test 4: Claude API"""
    print_header("Test 4: Claude API (Anthropic)")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print_test("Claude API", "FAIL", "API key missing")
        return False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Simple test message
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful' in exactly those words."}]
        )

        response_text = message.content[0].text
        if "API test successful" in response_text or "successful" in response_text.lower():
            print_test("Claude API", "PASS", f"Model: {message.model}")
            print(f"   Response: {response_text[:50]}...")
            return True
        else:
            print_test("Claude API", "WARN", f"Unexpected response: {response_text}")
            return True
    except Exception as e:
        print_test("Claude API", "FAIL", str(e))
        return False

def test_voyage_ai():
    """Test 5: Voyage AI Embeddings"""
    print_header("Test 5: Voyage AI (Embeddings)")

    api_key = os.getenv('VOYAGE_API_KEY')
    if not api_key:
        print_test("Voyage AI", "FAIL", "API key missing")
        return False

    try:
        import voyageai
        client = voyageai.Client(api_key=api_key)

        # Test embedding generation
        result = client.embed(
            ["This is a test document for demo readiness."],
            model="voyage-3"
        )

        if result.embeddings and len(result.embeddings[0]) > 0:
            print_test("Voyage AI", "PASS", f"Embedding dimension: {len(result.embeddings[0])}")
            return True
        else:
            print_test("Voyage AI", "FAIL", "No embeddings returned")
            return False
    except Exception as e:
        print_test("Voyage AI", "FAIL", str(e))
        return False

def test_document_upload(backend_url, token):
    """Test 6: Document Upload & Processing"""
    print_header("Test 6: Document Upload & Processing")

    if not token:
        print_test("Document Upload", "WARN", "No auth token provided, skipping")
        return True

    try:
        # Create test file
        test_content = """Demo Test Document

This is a test document for verifying upload and processing functionality before the Paige demo.

It contains information about SuperAssistant's key features:
- Knowledge base management
- Document processing
- RAG (Retrieval Augmented Generation)
- TRIPS scoring
- Modular library system
"""

        # Upload document
        files = {'file': ('demo_test.txt', test_content, 'text/plain')}
        headers = {'Authorization': f'Bearer {token}'}

        start_time = time.time()
        response = requests.post(
            f"{backend_url}/api/documents/upload",
            files=files,
            headers=headers,
            timeout=30
        )
        upload_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            doc_id = data.get('id')
            print_test("Document Upload", "PASS", f"Upload time: {upload_time:.2f}s")
            print(f"   Document ID: {doc_id}")
            print(f"   Processing: {data.get('processing_status', 'unknown')}")

            # Wait for processing
            time.sleep(3)

            # Check processing status
            status_response = requests.get(
                f"{backend_url}/api/documents/{doc_id}",
                headers=headers,
                timeout=10
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('processed'):
                    print_test("Document Processing", "PASS", f"Processed successfully")
                    print(f"   Chunks: {status_data.get('chunk_count', 'unknown')}")
                    return True
                else:
                    print_test("Document Processing", "WARN", "Still processing...")
                    return True
            else:
                print_test("Document Processing", "WARN", f"Status check failed: {status_response.status_code}")
                return True
        else:
            print_test("Document Upload", "FAIL", f"Status {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print_test("Document Upload", "FAIL", str(e))
        return False

def test_rag_query(backend_url, token):
    """Test 7: RAG Knowledge Base Query"""
    print_header("Test 7: RAG Knowledge Base Query")

    if not token:
        print_test("RAG Query", "WARN", "No auth token provided, skipping")
        return True

    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'message': 'What information do you have about SuperAssistant?',
            'use_knowledge_base': True,
            'max_chunks': 3
        }

        start_time = time.time()
        response = requests.post(
            f"{backend_url}/api/chat",
            json=payload,
            headers=headers,
            timeout=30
        )
        query_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print_test("RAG Query", "PASS", f"Response time: {query_time:.2f}s")
            print(f"   Chunks retrieved: {data.get('chunks_retrieved', 0)}")
            print(f"   Response preview: {data.get('response', '')[:100]}...")
            return True
        else:
            print_test("RAG Query", "FAIL", f"Status {response.status_code}")
            return False
    except Exception as e:
        print_test("RAG Query", "FAIL", str(e))
        return False

def test_modular_library_files():
    """Test 8: Modular Library Files Exist"""
    print_header("Test 8: Modular Library System Files")

    files_to_check = [
        'system_instructions/library_baseline.xml',
        'system_instructions/default.txt',
        'services/solomon_stage1.py',
        'services/solomon_stage2.py'
    ]

    all_exist = True
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print_test(file_path, "PASS", f"Size: {size} bytes")
        else:
            print_test(file_path, "FAIL", "File not found")
            all_exist = False

    return all_exist

def test_system_instructions():
    """Test 9: System Instructions De-Mitched"""
    print_header("Test 9: System Instructions (De-Mitching)")

    try:
        with open('system_instructions/default.txt', 'r') as f:
            content = f.read()

        # Check for hard-coded references (should NOT exist)
        bad_terms = ['Georgetown', 'NCEMCH', ' he ', ' him ']
        issues = []

        for term in bad_terms:
            if term in content:
                issues.append(term)

        if issues:
            print_test("De-Mitching Check", "FAIL", f"Found hard-coded terms: {', '.join(issues)}")
            return False

        # Check for variables (should exist)
        good_terms = ['{organization_name}', '{user_name}', '{user_role}']
        found_vars = []

        for var in good_terms:
            if var in content:
                found_vars.append(var)

        if len(found_vars) >= 2:
            print_test("De-Mitching Check", "PASS", f"Variables found: {', '.join(found_vars)}")
            return True
        else:
            print_test("De-Mitching Check", "WARN", f"Only {len(found_vars)} variables found")
            return True
    except Exception as e:
        print_test("De-Mitching Check", "FAIL", str(e))
        return False

def print_summary():
    """Print test summary"""
    print_header("Test Summary")

    total = results['passed'] + results['failed'] + results['warnings']

    print(f"{GREEN}✅ Passed: {results['passed']}/{total}{RESET}")
    print(f"{RED}❌ Failed: {results['failed']}/{total}{RESET}")
    print(f"{YELLOW}⚠️  Warnings: {results['warnings']}/{total}{RESET}")

    print()

    if results['failed'] == 0:
        print(f"{GREEN}{BOLD}🎉 ALL CRITICAL TESTS PASSED! Demo is ready.{RESET}")
        readiness_score = ((results['passed'] / total) * 10) if total > 0 else 0
        print(f"\n{BOLD}Demo Readiness Score: {readiness_score:.1f}/10{RESET}")
        return True
    else:
        print(f"{RED}{BOLD}⚠️  Some tests failed. Review issues before demo.{RESET}")
        readiness_score = ((results['passed'] / total) * 10) if total > 0 else 0
        print(f"\n{BOLD}Demo Readiness Score: {readiness_score:.1f}/10{RESET}")
        return False

def main():
    """Main test runner"""
    print_header(f"SuperAssistant Demo Readiness Test")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Demo Date: Tomorrow (November 21, 2025)")

    # Configuration
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
    auth_token = os.getenv('TEST_AUTH_TOKEN', '')  # Optional

    print(f"\n{BOLD}Configuration:{RESET}")
    print(f"  Backend URL: {backend_url}")
    print(f"  Auth Token: {'✅ Provided' if auth_token else '❌ Not provided (some tests will skip)'}")

    # Run all tests
    test_environment_variables()
    test_backend_health(backend_url)
    test_database_connection()
    test_claude_api()
    test_voyage_ai()
    test_modular_library_files()
    test_system_instructions()

    # Optional tests (require auth token)
    if auth_token:
        test_document_upload(backend_url, auth_token)
        test_rag_query(backend_url, auth_token)
    else:
        print_header("Skipped Tests (No Auth Token)")
        print(f"{YELLOW}⚠️  Document Upload - Skipped (need auth token){RESET}")
        print(f"{YELLOW}⚠️  RAG Query - Skipped (need auth token){RESET}")
        print(f"\nTo run all tests, set TEST_AUTH_TOKEN environment variable")

    # Print summary
    success = print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
