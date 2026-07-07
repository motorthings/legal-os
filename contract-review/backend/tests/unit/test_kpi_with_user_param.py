"""
Test KPI endpoints with user_id parameter
Tests that admin can query Charlie's KPI data
"""
import requests

BACKEND_URL = "http://localhost:8000"  # Adjust if needed
SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"

# First, verify Charlie has conversations
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

url = f"{SUPABASE_URL}/rest/v1/conversations"
params = {
    "user_id": f"eq.{CHARLIE_USER_ID}",
    "select": "id,title,created_at"
}

response = requests.get(url, headers=headers, params=params)
conversations = response.json()

print(f"✅ Charlie has {len(conversations)} conversations in the database\n")

# Now test the KPI endpoints
# Note: You'll need to run the backend server and have a valid JWT token
# This is a demonstration of the API call structure

print("To test the KPI endpoints with the user_id parameter:")
print(f"\n1. Ideation Velocity:")
print(f"   GET {BACKEND_URL}/api/kpis/ideation-velocity?user_id={CHARLIE_USER_ID}&time_period=month")
print(f"\n2. Correction Loop:")
print(f"   GET {BACKEND_URL}/api/kpis/correction-loop?user_id={CHARLIE_USER_ID}")

print("\n📌 These endpoints require authentication. Use a JWT token in the Authorization header.")
print("📌 The token must be from an admin user who has permission to query other users' data.")
