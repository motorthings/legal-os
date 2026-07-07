import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

# Load the synthetic conversations JSON
with open('synthetic_conversations_charlie.json', 'r') as f:
    synthetic_conversations = json.load(f)

expected_titles = [conv['title'] for conv in synthetic_conversations]

print("📋 Expected synthetic conversation titles:")
for i, title in enumerate(expected_titles, 1):
    print(f"  {i}. {title}")

print("\n" + "="*80)

# Get all conversations for Charlie
conv_url = f"{SUPABASE_URL}/rest/v1/conversations"
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "user_id": "eq.d3ba5354-873a-435a-a36a-853373c4f6e5",
    "select": "id,title,created_at",
    "order": "created_at.desc",
    "limit": 30
}

conv_response = requests.get(conv_url, headers=headers, params=params)
all_conversations = conv_response.json()

print(f"\n🔍 Found {len(all_conversations)} total conversations in database")
print("\n📊 Matching synthetic conversations:\n")

matched = []
unmatched = []

for conv in all_conversations:
    if conv['title'] in expected_titles:
        matched.append(conv)
        print(f"✅ MATCH: {conv['title']}")
        print(f"   Created: {conv['created_at'][:10]}")
        # Get message count
        msg_url = f"{SUPABASE_URL}/rest/v1/messages"
        msg_params = {
            "conversation_id": f"eq.{conv['id']}",
            "select": "id"
        }
        msg_response = requests.get(msg_url, headers=headers, params=msg_params)
        msg_count = len(msg_response.json())
        print(f"   Messages: {msg_count}")
        print()
    else:
        unmatched.append(conv)

print(f"\n📈 Summary:")
print(f"  Expected synthetic conversations: {len(expected_titles)}")
print(f"  Found matching in database: {len(matched)}")
print(f"  Missing: {len(expected_titles) - len(matched)}")

if len(expected_titles) - len(matched) > 0:
    print(f"\n❌ Missing conversations:")
    matched_titles = [c['title'] for c in matched]
    for title in expected_titles:
        if title not in matched_titles:
            print(f"  - {title}")

print(f"\n📝 Other conversations (not synthetic):")
for conv in unmatched[:10]:
    print(f"  - {conv['title']} ({conv['created_at'][:10]})")

