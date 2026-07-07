import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"

# Query conversations for Charlie
url = f"{SUPABASE_URL}/rest/v1/conversations"
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "user_id": f"eq.{CHARLIE_USER_ID}",
    "select": "id,title,created_at",
    "order": "created_at.desc",
    "limit": 15
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    conversations = response.json()
    print(f"✅ Found {len(conversations)} conversations for Charlie")
    print()
    for i, conv in enumerate(conversations[:10], 1):
        print(f"{i}. {conv['title']}")
        print(f"   ID: {conv['id']}")
        print(f"   Created: {conv['created_at']}")
        print()
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
