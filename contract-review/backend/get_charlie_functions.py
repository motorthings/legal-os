import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_CLIENT_ID = "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b"

# Query system instructions for Charlie's client
url = f"{SUPABASE_URL}/rest/v1/system_instructions"
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "client_id": f"eq.{CHARLIE_CLIENT_ID}",
    "select": "id,content,created_at",
    "order": "created_at.desc",
    "limit": 1
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    instructions = response.json()
    if instructions:
        content = instructions[0]['content']
        print("✅ Found Charlie's system instructions")
        print()
        
        # Extract function names from the content
        import re
        functions = re.findall(r'<function name="([^"]+)"', content)
        
        if functions:
            print(f"📋 Charlie's configured functions ({len(functions)} total):")
            for i, func in enumerate(functions, 1):
                print(f"{i}. {func}")
        else:
            print("⚠️  No functions found in system instructions")
            print()
            print("First 500 chars of content:")
            print(content[:500])
    else:
        print("❌ No system instructions found for Charlie")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
