"""Direct Supabase connection test to debug RLS issues"""
import os
from supabase import create_client

# Test both keys
supabase_url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 80)
print("Supabase Connection Test")
print("=" * 80)
print(f"URL: {supabase_url}")
print(f"Anon Key Length: {len(anon_key) if anon_key else 0} chars")
print(f"Service Key Length: {len(service_key) if service_key else 0} chars")
print(f"Keys are same: {anon_key == service_key}")
print()

# Test with service role key
print("Testing with SERVICE ROLE key...")
try:
    client = create_client(supabase_url, service_key)
    response = client.table('users').select('id, email, role').limit(5).execute()
    print(f"✅ SUCCESS: Found {len(response.data)} users")
    for user in response.data:
        print(f"   - {user.get('email')} ({user.get('role')})")
except Exception as e:
    print(f"❌ FAILED: {e}")

print()

# Test with anon key
print("Testing with ANON key...")
try:
    client = create_client(supabase_url, anon_key)
    response = client.table('users').select('id, email, role').limit(5).execute()
    print(f"✅ SUCCESS: Found {len(response.data)} users")
    for user in response.data:
        print(f"   - {user.get('email')} ({user.get('role')})")
except Exception as e:
    print(f"❌ FAILED: {e}")
