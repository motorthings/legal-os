"""
Test script for KPI Dashboard implementation
Tests database access, query logic, and data flow
"""
import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase

def test_database_schema():
    """Test that required tables and columns exist"""
    print("\n=== Testing Database Schema ===\n")

    supabase = get_supabase()

    # Test conversations table structure
    print("1. Testing conversations table...")
    try:
        result = supabase.table('conversations').select('*').limit(1).execute()
        if result.data:
            print(f"   ✓ Conversations table exists")
            print(f"   Columns: {list(result.data[0].keys())}")

            # Check for required columns
            has_user_id = 'user_id' in result.data[0]
            has_client_id = 'client_id' in result.data[0]

            print(f"   - has user_id: {has_user_id}")
            print(f"   - has client_id: {has_client_id}")

            if not has_user_id and not has_client_id:
                print(f"   ✗ ERROR: Missing both user_id and client_id!")
                return False
        else:
            print(f"   ℹ No data in conversations table")
    except Exception as e:
        print(f"   ✗ Error accessing conversations: {e}")
        return False

    # Test messages table structure
    print("\n2. Testing messages table...")
    try:
        result = supabase.table('messages').select('*').limit(1).execute()
        if result.data:
            print(f"   ✓ Messages table exists")
            print(f"   Columns: {list(result.data[0].keys())}")
        else:
            print(f"   ℹ No data in messages table")
    except Exception as e:
        print(f"   ✗ Error accessing messages: {e}")
        return False

    # Test users table structure
    print("\n3. Testing users table...")
    try:
        result = supabase.table('users').select('id, client_id').limit(1).execute()
        if result.data:
            print(f"   ✓ Users table exists")
            print(f"   Sample user has client_id: {'client_id' in result.data[0]}")
        else:
            print(f"   ℹ No data in users table")
    except Exception as e:
        print(f"   ✗ Error accessing users: {e}")
        return False

    return True


def test_conversation_data():
    """Test actual conversation data for KPI calculations"""
    print("\n=== Testing Conversation Data ===\n")

    supabase = get_supabase()

    # Get total conversations
    try:
        result = supabase.table('conversations').select('id, user_id', count='exact').execute()
        total_convs = result.count
        print(f"Total conversations: {total_convs}")

        if total_convs == 0:
            print("  ⚠ WARNING: No conversations in database - KPIs will show no data")
            return True  # Not an error, just no data yet

        # Get conversations with messages
        print(f"\n1. Checking conversations have messages...")
        result = supabase.table('messages').select('conversation_id', count='exact').execute()
        total_messages = result.count
        print(f"   Total messages: {total_messages}")

        if total_messages == 0:
            print("   ⚠ WARNING: No messages found - Correction Loop KPI will be empty")

        # Check for strategic keywords in messages
        print(f"\n2. Checking for strategic work indicators...")
        strategic_keywords = [
            'conceptual', 'model', 'framework', 'strategy',
            'plan', 'draft', 'report', 'brief', 'memo'
        ]

        messages_result = supabase.table('messages').select(
            'id, content, conversation_id'
        ).eq('role', 'user').limit(100).execute()

        strategic_count = 0
        for msg in messages_result.data:
            content_lower = msg['content'].lower()
            if any(kw in content_lower for kw in strategic_keywords):
                strategic_count += 1

        print(f"   Messages with strategic keywords: {strategic_count}/{len(messages_result.data)}")

        if strategic_count == 0:
            print("   ⚠ WARNING: No strategic keywords found - Ideation Velocity will be 0")

        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_kpi_query_logic():
    """Test the actual KPI query logic"""
    print("\n=== Testing KPI Query Logic ===\n")

    supabase = get_supabase()

    # Test Ideation Velocity logic
    print("1. Testing Ideation Velocity query...")
    try:
        # Get a sample user
        users_result = supabase.table('users').select('id, client_id').limit(1).execute()

        if not users_result.data:
            print("   ⚠ No users in database")
            return True

        sample_user = users_result.data[0]
        user_id = sample_user['id']
        client_id = sample_user.get('client_id')

        print(f"   Testing with user_id: {user_id}")
        print(f"   User has client_id: {client_id is not None}")

        # Try the query approach from kpis.py
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()

        messages_result = supabase.table('messages').select(
            'id, conversation_id, content, created_at'
        ).eq('role', 'user').gte('created_at', start_date).limit(50).execute()

        print(f"   Found {len(messages_result.data)} user messages in last 30 days")

        # Filter for strategic keywords
        strategic_keywords = [
            'conceptual', 'model', 'framework', 'strategy',
            'plan', 'draft', 'report', 'brief', 'memo'
        ]

        strategic_convs = set()
        for msg in messages_result.data:
            content_lower = msg['content'].lower()
            if any(kw in content_lower for kw in strategic_keywords):
                strategic_convs.add(msg['conversation_id'])

        print(f"   Strategic conversations: {len(strategic_convs)}")
        print(f"   ✓ Ideation Velocity query logic works")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test Correction Loop logic
    print("\n2. Testing Correction Loop query...")
    try:
        # The bug: queries by client_id instead of user_id
        print("   Testing CURRENT implementation (using client_id)...")

        if client_id:
            # This is what the current code does - query by client_id
            conversations_result = supabase.table('conversations').select(
                'id, created_at'
            ).eq('client_id', client_id).execute()

            if 'code' in conversations_result.__dict__ and conversations_result.code == 'PGRST116':
                print("   ✗ ERROR: Column 'client_id' does not exist in conversations table!")
                print("   This confirms the bug: kpis.py line 199 queries wrong column")
                return False

            print(f"   Found {len(conversations_result.data)} conversations by client_id")

        print("\n   Testing CORRECT implementation (using user_id)...")
        # This is what it SHOULD do - query by user_id
        conversations_result = supabase.table('conversations').select(
            'id, user_id, created_at'
        ).eq('user_id', user_id).execute()

        print(f"   Found {len(conversations_result.data)} conversations by user_id")

        if conversations_result.data:
            # Count turns for first conversation
            conv_id = conversations_result.data[0]['id']
            messages_result = supabase.table('messages').select(
                'id, role'
            ).eq('conversation_id', conv_id).execute()

            user_turns = len([m for m in messages_result.data if m['role'] == 'user'])
            print(f"   Sample conversation has {user_turns} user turns")
            print(f"   ✓ Correction Loop query logic works (with correct column)")
        else:
            print("   ℹ No conversations for this user")

        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("KPI DASHBOARD IMPLEMENTATION TEST")
    print("="*60)

    # Check environment
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_KEY'):
        print("\n✗ ERROR: Missing Supabase credentials")
        print("Required: SUPABASE_URL and SUPABASE_SERVICE_KEY")
        return False

    # Run tests
    tests = [
        ("Database Schema", test_database_schema),
        ("Conversation Data", test_conversation_data),
        ("KPI Query Logic", test_kpi_query_logic),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✓ All tests passed")
    else:
        print("\n✗ Some tests failed - see details above")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
