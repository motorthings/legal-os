import requests
import json
import re

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"
CHARLIE_CLIENT_ID = "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Try extractions table
print("🔍 Checking extractions table...")
url = f"{SUPABASE_URL}/rest/v1/extractions"
params = {
    "client_id": f"eq.{CHARLIE_CLIENT_ID}",
    "select": "id,status,generated_instructions,selected_functions,created_at",
    "order": "created_at.desc",
    "limit": 5
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    extractions = response.json()
    if extractions:
        print(f"✅ Found {len(extractions)} extraction(s)")
        for i, ext in enumerate(extractions, 1):
            print(f"\n{i}. Extraction ID: {ext['id']}")
            print(f"   Status: {ext.get('status', 'N/A')}")
            print(f"   Created: {ext.get('created_at', 'N/A')}")
            
            if ext.get('selected_functions'):
                funcs = ext.get('selected_functions')
                if isinstance(funcs, list):
                    print(f"   Functions: {', '.join(funcs[:5])}")
                else:
                    print(f"   Functions: {funcs}")
            
            if ext.get('generated_instructions'):
                instructions = ext.get('generated_instructions')
                # Extract function names from instructions
                functions = re.findall(r'<function name="([^"]+)"', instructions)
                if functions:
                    print(f"   📋 Functions in instructions: {', '.join(functions)}")
    else:
        print("❌ No extractions found")
else:
    print(f"❌ Error: {response.status_code}")

# Also check clients table again more carefully
print("\n\n🔍 Re-checking clients table...")
url = f"{SUPABASE_URL}/rest/v1/clients"
params = {
    "id": f"eq.{CHARLIE_CLIENT_ID}",
    "select": "*"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    clients = response.json()
    if clients:
        client = clients[0]
        print("✅ Client found:")
        print(f"   Name: {client.get('name')}")
        print(f"   Email: {client.get('email')}")
        if client.get('system_instructions'):
            instructions = client['system_instructions']
            functions = re.findall(r'<function name="([^"]+)"', instructions)
            print(f"   📋 Functions: {', '.join(functions) if functions else 'None found'}")
            print(f"   Instructions length: {len(instructions)} characters")
        else:
            print("   ⚠️  system_instructions field is empty")
