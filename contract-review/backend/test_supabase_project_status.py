"""
Check Supabase project status and configuration
"""
import os
import requests

supabase_url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 80)
print("Supabase Project Status Check")
print("=" * 80)

# Test 1: Check if project is active (try health endpoint)
print("\n1. Testing Project Health")
print("-" * 80)
try:
    response = requests.get(f"{supabase_url}/rest/v1/", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Check auth endpoints
print("\n2. Testing Auth Endpoints")
print("-" * 80)
try:
    response = requests.get(
        f"{supabase_url}/auth/v1/health",
        headers={"apikey": service_key},
        timeout=5
    )
    print(f"Auth Health Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Try a simple RPC call instead of table access
print("\n3. Testing RPC Functions")
print("-" * 80)
try:
    # Try to call a built-in function
    response = requests.post(
        f"{supabase_url}/rest/v1/rpc/version",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json"
        },
        json={},
        timeout=5
    )
    print(f"RPC Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Check the actual error details from Supabase
print("\n4. Detailed Error Analysis")
print("-" * 80)
try:
    response = requests.get(
        f"{supabase_url}/rest/v1/users?select=id&limit=1",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=5
    )
    print(f"Status Code: {response.status_code}")
    print(f"Status Text: {response.reason}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print(f"\nResponse Body: {response.text}")

    # Check for Cloudflare or other proxy headers
    if 'cf-ray' in response.headers:
        print("\n⚠️ Request is going through Cloudflare")
    if 'x-kong' in response.headers or any('kong' in k.lower() for k in response.headers.keys()):
        print("\n⚠️ Request is going through Kong Gateway")

except Exception as e:
    print(f"Error: {e}")

# Test 5: Check if we can access via GraphQL instead
print("\n5. Testing GraphQL Endpoint")
print("-" * 80)
try:
    response = requests.post(
        f"{supabase_url}/graphql/v1",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json"
        },
        json={
            "query": "{ __schema { types { name } } }"
        },
        timeout=5
    )
    print(f"GraphQL Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("POSSIBLE ISSUES:")
print("=" * 80)
print("""
If all endpoints return 403:
1. ⚠️ Supabase project might be PAUSED
2. ⚠️ API access might be restricted by IP allowlist
3. ⚠️ Project might have billing issues
4. ⚠️ API might be disabled in project settings

Check Supabase Dashboard:
- Project Settings → General → Project Status
- Project Settings → API → API Settings
- Project Settings → API → Allowed IP addresses
""")
