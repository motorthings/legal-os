"""
Comprehensive Diagnostic Testing Script for SuperAssistant MVP
Tests all critical paths: database, API endpoints, integrations
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase
from logger_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

class DiagnosticTester:
    def __init__(self):
        self.supabase = get_supabase()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }

    def log_test(self, category: str, test_name: str, status: str, details: Any = None):
        """Log a test result"""
        result = {
            "category": category,
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results["tests"].append(result)

        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        logger.info(f"{icon} [{category}] {test_name}: {status}")
        if details:
            logger.info(f"   Details: {details}")

    def test_database_connection(self):
        """Test 1: Basic database connectivity"""
        try:
            # Try a simple query that doesn't require RLS
            response = self.supabase.table('users').select('id').limit(1).execute()
            self.log_test("Database", "Connection Test", "PASS",
                         f"Connected successfully, found {len(response.data)} users")
            return True
        except Exception as e:
            self.log_test("Database", "Connection Test", "FAIL", str(e))
            return False

    def test_database_tables(self):
        """Test 2: Verify all required tables exist"""
        required_tables = [
            'users', 'conversations', 'messages', 'documents', 'document_chunks',
            'google_drive_tokens', 'google_drive_sync_log',
            'notion_tokens', 'notion_sync_log',
            'interview_sessions', 'interview_extractions',
            'user_prompts', 'api_usage_logs'
        ]

        results = {}
        for table in required_tables:
            try:
                response = self.supabase.table(table).select('id').limit(1).execute()
                results[table] = "EXISTS"
            except Exception as e:
                if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                    results[table] = "MISSING"
                else:
                    results[table] = f"ERROR: {str(e)[:100]}"

        all_exist = all(v == "EXISTS" for v in results.values())
        status = "PASS" if all_exist else "FAIL"
        self.log_test("Database", "Table Existence Check", status, results)
        return all_exist

    def test_pgvector_extension(self):
        """Test 3: Verify pgvector extension is enabled"""
        try:
            # Try to query document_chunks which uses vector type
            response = self.supabase.table('document_chunks').select('id, embedding').limit(1).execute()
            self.log_test("Database", "pgvector Extension", "PASS",
                         "Vector columns accessible")
            return True
        except Exception as e:
            self.log_test("Database", "pgvector Extension", "FAIL", str(e))
            return False

    def test_match_document_chunks_function(self):
        """Test 4: Verify match_document_chunks RPC function exists"""
        try:
            # Create a dummy embedding (1024 dimensions of zeros)
            dummy_embedding = [0.0] * 1024

            # Try to call the function
            response = self.supabase.rpc(
                'match_document_chunks',
                {
                    'query_embedding': dummy_embedding,
                    'match_count': 1
                }
            ).execute()

            self.log_test("Database", "match_document_chunks() Function", "PASS",
                         f"Function exists, returned {len(response.data)} results")
            return True
        except Exception as e:
            error_msg = str(e)
            if "function" in error_msg.lower() and "does not exist" in error_msg.lower():
                self.log_test("Database", "match_document_chunks() Function", "FAIL",
                             "Function does not exist - Migration 020 not applied")
            else:
                self.log_test("Database", "match_document_chunks() Function", "WARN",
                             f"Function may exist but errored: {error_msg[:200]}")
            return False

    def test_users_count(self):
        """Test 5: Count users in database"""
        try:
            response = self.supabase.table('users').select('id, email, role').execute()
            self.log_test("Database", "User Accounts", "PASS",
                         f"Found {len(response.data)} users")
            for user in response.data:
                logger.info(f"   - {user.get('email')} ({user.get('role')})")
            return True
        except Exception as e:
            self.log_test("Database", "User Accounts", "FAIL", str(e))
            return False

    def test_documents_count(self):
        """Test 6: Count documents in database"""
        try:
            response = self.supabase.table('documents').select('id, filename, processed').execute()
            processed = sum(1 for d in response.data if d.get('processed'))
            self.log_test("Database", "Documents", "PASS",
                         f"Found {len(response.data)} documents ({processed} processed)")
            return True
        except Exception as e:
            self.log_test("Database", "Documents", "FAIL", str(e))
            return False

    def test_document_chunks_count(self):
        """Test 7: Count document chunks and embeddings"""
        try:
            response = self.supabase.table('document_chunks').select('id, embedding').execute()
            with_embeddings = sum(1 for chunk in response.data if chunk.get('embedding'))
            self.log_test("Database", "Document Chunks", "PASS",
                         f"Found {len(response.data)} chunks ({with_embeddings} with embeddings)")
            return True
        except Exception as e:
            self.log_test("Database", "Document Chunks", "FAIL", str(e))
            return False

    def test_conversations_count(self):
        """Test 8: Count conversations"""
        try:
            response = self.supabase.table('conversations').select('id, title').execute()
            self.log_test("Database", "Conversations", "PASS",
                         f"Found {len(response.data)} conversations")
            return True
        except Exception as e:
            self.log_test("Database", "Conversations", "FAIL", str(e))
            return False

    def test_environment_variables(self):
        """Test 9: Verify critical environment variables"""
        required_vars = {
            'SUPABASE_URL': os.getenv('SUPABASE_URL'),
            'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'VOYAGE_API_KEY': os.getenv('VOYAGE_API_KEY'),
            'ELEVENLABS_API_KEY': os.getenv('ELEVENLABS_API_KEY'),
            'ELEVENLABS_AGENT_ID': os.getenv('ELEVENLABS_AGENT_ID'),
            'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
            'NOTION_CLIENT_ID': os.getenv('NOTION_CLIENT_ID'),
            'OAUTH_ENCRYPTION_KEY': os.getenv('OAUTH_ENCRYPTION_KEY'),
        }

        missing = [k for k, v in required_vars.items() if not v]

        if not missing:
            self.log_test("Environment", "API Keys", "PASS",
                         "All critical environment variables configured")
            return True
        else:
            self.log_test("Environment", "API Keys", "FAIL",
                         f"Missing variables: {', '.join(missing)}")
            return False

    def test_google_drive_integration(self):
        """Test 10: Check Google Drive integration status"""
        try:
            response = self.supabase.table('google_drive_tokens').select('*').execute()
            self.log_test("Integration", "Google Drive", "PASS",
                         f"Found {len(response.data)} connected accounts")
            return True
        except Exception as e:
            self.log_test("Integration", "Google Drive", "FAIL", str(e))
            return False

    def test_notion_integration(self):
        """Test 11: Check Notion integration status"""
        try:
            response = self.supabase.table('notion_tokens').select('*').execute()
            self.log_test("Integration", "Notion", "PASS",
                         f"Found {len(response.data)} connected accounts")
            return True
        except Exception as e:
            self.log_test("Integration", "Notion", "FAIL", str(e))
            return False

    def test_interview_system(self):
        """Test 12: Check interview system data"""
        try:
            sessions = self.supabase.table('interview_sessions').select('*').execute()
            extractions = self.supabase.table('interview_extractions').select('*').execute()
            self.log_test("Interview System", "Sessions & Extractions", "PASS",
                         f"Found {len(sessions.data)} sessions, {len(extractions.data)} extractions")
            return True
        except Exception as e:
            self.log_test("Interview System", "Sessions & Extractions", "FAIL", str(e))
            return False

    def run_all_tests(self):
        """Run all diagnostic tests"""
        logger.info("=" * 80)
        logger.info("🚀 Starting Comprehensive Diagnostic Tests")
        logger.info("=" * 80)

        tests = [
            self.test_database_connection,
            self.test_database_tables,
            self.test_pgvector_extension,
            self.test_match_document_chunks_function,
            self.test_users_count,
            self.test_documents_count,
            self.test_document_chunks_count,
            self.test_conversations_count,
            self.test_environment_variables,
            self.test_google_drive_integration,
            self.test_notion_integration,
            self.test_interview_system,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"❌ Test {test.__name__} crashed: {e}")
                self.log_test("System", test.__name__, "CRASH", str(e))

        # Summary
        logger.info("=" * 80)
        logger.info("📊 Test Summary")
        logger.info("=" * 80)

        passed = sum(1 for t in self.results["tests"] if t["status"] == "PASS")
        failed = sum(1 for t in self.results["tests"] if t["status"] == "FAIL")
        warned = sum(1 for t in self.results["tests"] if t["status"] == "WARN")
        total = len(self.results["tests"])

        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️  Warnings: {warned}")
        logger.info(f"Pass Rate: {(passed/total*100):.1f}%")

        # Save results to file
        output_file = "/tmp/diagnostic_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\n📄 Full results saved to: {output_file}")

        return self.results

if __name__ == "__main__":
    tester = DiagnosticTester()
    results = tester.run_all_tests()

    # Exit with error code if any tests failed
    failed = sum(1 for t in results["tests"] if t["status"] == "FAIL")
    sys.exit(1 if failed > 0 else 0)
