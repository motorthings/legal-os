import requests
import json
import re

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_CLIENT_ID = "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b"

# Query clients table for Charlie's system instructions
url = f"{SUPABASE_URL}/rest/v1/clients"
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "id": f"eq.{CHARLIE_CLIENT_ID}",
    "select": "id,name,organization,system_instructions"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    clients = response.json()
    if clients:
        client = clients[0]
        print(f"✅ Found client: {client.get('name', 'N/A')}")
        print(f"   Organization: {client.get('organization', 'N/A')}")
        print()
        
        system_instructions = client.get('system_instructions', '')
        if system_instructions:
            # Extract function names
            functions = re.findall(r'<function name="([^"]+)"', system_instructions)
            
            if functions:
                print(f"📋 Charlie's configured functions ({len(functions)} total):")
                for i, func in enumerate(functions, 1):
                    print(f"   {i}. {func}")
                print()
            else:
                print("⚠️  No functions found in format <function name=\"...\">")
                print()
                # Try alternative pattern
                functions_alt = re.findall(r'function:\s*(\w+)', system_instructions, re.IGNORECASE)
                if functions_alt:
                    print(f"Found {len(functions_alt)} functions with alternative pattern:")
                    for f in functions_alt[:10]:
                        print(f"   - {f}")
                else:
                    print("First 1000 chars of system_instructions:")
                    print(system_instructions[:1000])
        else:
            print("⚠️  No system_instructions field found or it's empty")
    else:
        print("❌ No client found with that ID")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
