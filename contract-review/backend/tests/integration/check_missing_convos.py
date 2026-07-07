import requests

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Check for the missing conversations by ID
missing_ids = [
    "168c00f0-0b9d-4c19-aa2d-6a17fecb2198",  # Framework for Partnership Evaluation
    "5a4f6c71-c04f-460b-b04f-5eeb973005f4",  # Reframing Product Roadmap
]

for conv_id in missing_ids:
    url = f"{SUPABASE_URL}/rest/v1/conversations"
    params = {"id": f"eq.{conv_id}", "select": "id,title,created_at,user_id"}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200 and response.json():
        conv = response.json()[0]
        print(f"✅ Found: {conv['title']}")
        print(f"   ID: {conv['id']}")
        print(f"   User ID: {conv['user_id']}")
        print(f"   Created: {conv['created_at']}")
    else:
        print(f"❌ Not found: {conv_id}")
    print()
