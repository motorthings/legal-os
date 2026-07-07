"""
Get a test user ID from the database for testing

This script queries the database to find an existing user
that can be used for testing.
"""

from database import get_supabase
from dotenv import load_dotenv

load_dotenv()

def get_test_user():
    """Get the first available user from the database"""
    try:
        supabase = get_supabase()
        result = supabase.table('users').select('id, email, role, client_id').limit(1).execute()

        if result.data and len(result.data) > 0:
            user = result.data[0]
            print("✅ Found test user:")
            print(f"   User ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Role: {user['role']}")
            print(f"   Client ID: {user.get('client_id', 'None')}")
            return user
        else:
            print("❌ No users found in database")
            print("   You may need to create a test user first")
            return None

    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return None

if __name__ == "__main__":
    user = get_test_user()
    if user:
        print(f"\nTo generate a token for this user:")
        print(f"./venv/bin/python3 generate_test_token.py '{user['id']}' '{user['email']}'")
