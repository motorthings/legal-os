import requests
import json
import re

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_CLIENT_ID = "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Query interview_extractions table
print("🔍 Checking interview_extractions table...")
url = f"{SUPABASE_URL}/rest/v1/interview_extractions"
params = {
    "client_id": f"eq.{CHARLIE_CLIENT_ID}",
    "select": "*",
    "order": "created_at.desc",
    "limit": 5
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    extractions = response.json()
    if extractions:
        print(f"✅ Found {len(extractions)} extraction(s)\n")
        for i, ext in enumerate(extractions, 1):
            print(f"{'='*60}")
            print(f"Extraction #{i}")
            print(f"{'='*60}")
            print(f"ID: {ext['id']}")
            print(f"Status: {ext.get('status', 'N/A')}")
            print(f"Created: {ext.get('created_at', 'N/A')}")
            print()
            
            # Check for extraction_json
            if 'extraction_json' in ext and ext['extraction_json']:
                ej = ext['extraction_json']
                if isinstance(ej, dict):
                    print("📋 Extraction Data:")
                    if 'pain_points' in ej:
                        print(f"   Pain points: {len(ej['pain_points'])} items")
                    if 'leadership_styles' in ej:
                        print(f"   Leadership styles: {len(ej['leadership_styles'])} items")
                print()
            
            # Check for selected_functions
            if 'selected_functions' in ext and ext['selected_functions']:
                funcs = ext['selected_functions']
                print(f"🎯 Selected Functions ({len(funcs)} total):")
                for f in funcs:
                    print(f"   - {f}")
                print()
            
            # Check for generated_instructions
            if 'generated_instructions' in ext and ext['generated_instructions']:
                instructions = ext['generated_instructions']
                functions = re.findall(r'<function name="([^"]+)"', instructions)
                if functions:
                    print(f"📝 Functions in Generated Instructions ({len(functions)} total):")
                    for f in functions:
                        print(f"   - {f}")
                print(f"\n   Instructions length: {len(instructions):,} characters")
                print()
    else:
        print("❌ No extractions found for Charlie")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
