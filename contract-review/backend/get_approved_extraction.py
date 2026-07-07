import requests
import json
import re

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
EXTRACTION_ID = "5c615335-e299-43c0-b7d8-408ab7763798"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Get the specific approved extraction
url = f"{SUPABASE_URL}/rest/v1/interview_extractions"
params = {
    "id": f"eq.{EXTRACTION_ID}",
    "select": "*"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    extractions = response.json()
    if extractions:
        ext = extractions[0]
        print("✅ Found approved extraction\n")
        print("All available fields:")
        for key in sorted(ext.keys()):
            value = ext[key]
            if key == 'generated_instructions' and value:
                print(f"\n{key}:")
                # Extract functions from generated instructions
                functions = re.findall(r'<function name="([^"]+)"', value)
                if functions:
                    print(f"   Found {len(functions)} functions:")
                    for i, f in enumerate(functions, 1):
                        print(f"      {i}. {f}")
                print(f"   (Full length: {len(value):,} characters)")
            elif key == 'selected_functions' and value:
                print(f"\n{key}:")
                if isinstance(value, list):
                    for i, f in enumerate(value, 1):
                        print(f"   {i}. {f}")
                else:
                    print(f"   {value}")
            elif isinstance(value, (dict, list)):
                print(f"\n{key}: {json.dumps(value, indent=2)[:500]}...")
            else:
                val_str = str(value)
                if len(val_str) > 100:
                    print(f"{key}: {val_str[:100]}...")
                else:
                    print(f"{key}: {val_str}")
    else:
        print("❌ Extraction not found")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
