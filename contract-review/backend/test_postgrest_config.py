"""
Deep diagnostic for PostgREST API configuration issues
Tests JWT tokens, API endpoints, and headers
"""
import os
import json
import base64
import requests

def decode_jwt(token):
    """Decode JWT without verification to inspect claims"""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return {"error": str(e)}

# Get environment variables
supabase_url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 80)
print("PostgREST API Configuration Diagnostic")
print("=" * 80)

# Decode both tokens
print("\n1. JWT Token Analysis")
print("-" * 80)

print("\nANON KEY:")
anon_claims = decode_jwt(anon_key)
print(json.dumps(anon_claims, indent=2))

print("\nSERVICE ROLE KEY:")
service_claims = decode_jwt(service_key)
print(json.dumps(service_claims, indent=2))

print("\nKeys are identical:", anon_key == service_key)

# Test direct API calls
print("\n2. Direct PostgREST API Tests")
print("-" * 80)

# Build the REST endpoint URL
rest_url = f"{supabase_url}/rest/v1/users"

# Test 1: With anon key
print(f"\nTest 1: GET {rest_url} with ANON key")
try:
    response = requests.get(
        rest_url,
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        params={"select": "id,email,role", "limit": 1}
    )
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    if response.status_code == 200:
        print(f"Success! Data: {response.json()}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# Test 2: With service role key
print(f"\nTest 2: GET {rest_url} with SERVICE ROLE key")
try:
    response = requests.get(
        rest_url,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        params={"select": "id,email,role", "limit": 1}
    )
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    if response.status_code == 200:
        print(f"Success! Data: {response.json()}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# Test 3: Try different endpoint formats
print("\n3. Testing Alternative Endpoint Formats")
print("-" * 80)

endpoints = [
    f"{supabase_url}/rest/v1/users",
    f"{supabase_url}/rest/v1/rpc/users",
]

for endpoint in endpoints:
    print(f"\nTrying: {endpoint}")
    try:
        response = requests.get(
            endpoint,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
            params={"select": "id", "limit": 1},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ SUCCESS!")
            break
    except Exception as e:
        print(f"Failed: {e}")

# Test 4: Check if we can access public schema info
print("\n4. Testing Schema Access")
print("-" * 80)

# Try to get table info
try:
    response = requests.options(
        f"{supabase_url}/rest/v1/",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    print(f"OPTIONS request status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
except Exception as e:
    print(f"Failed: {e}")

print("\n" + "=" * 80)
print("Diagnostic Complete")
print("=" * 80)
