import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

# Load the v2 synthetic conversations JSON
with open('synthetic_conversations_charlie_v2.json', 'r') as f:
    v2_conversations = json.load(f)

expected_titles = [conv['title'] for conv in v2_conversations]

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
    "order": "created_at.asc",
    "limit": 50
}

conv_response = requests.get(conv_url, headers=headers, params=params)
all_conversations = conv_response.json()

print("="*80)
print("V2 SYNTHETIC CONVERSATIONS VERIFICATION")
print("="*80)

matched = []
for expected_title in expected_titles:
    found = False
    for conv in all_conversations:
        if conv['title'] == expected_title:
            found = True
            matched.append(conv)
            
            # Get messages
            msg_url = f"{SUPABASE_URL}/rest/v1/messages"
            msg_params = {
                "conversation_id": f"eq.{conv['id']}",
                "select": "role,content",
                "order": "timestamp.asc"
            }
            msg_response = requests.get(msg_url, headers=headers, params=msg_params)
            messages = msg_response.json()
            
            print(f"\n✅ {expected_title}")
            print(f"   Created: {conv['created_at'][:10]}")
            print(f"   Messages: {len(messages)}")
            
            # Count user vs assistant messages
            user_msgs = [m for m in messages if m['role'] == 'user']
            asst_msgs = [m for m in messages if m['role'] == 'assistant']
            print(f"   User messages: {len(user_msgs)}")
            print(f"   Assistant messages: {len(asst_msgs)}")
            
            # Show a content sample
            if len(messages) > 0:
                first_user = next((m for m in messages if m['role'] == 'user'), None)
                first_asst = next((m for m in messages if m['role'] == 'assistant'), None)
                
                if first_user:
                    preview = first_user['content'][:100] + "..." if len(first_user['content']) > 100 else first_user['content']
                    print(f"   User: {preview}")
                
                if first_asst:
                    preview = first_asst['content'][:100] + "..." if len(first_asst['content']) > 100 else first_asst['content']
                    print(f"   Assistant: {preview}")
            break
    
    if not found:
        print(f"\n❌ MISSING: {expected_title}")

print("\n" + "="*80)
print(f"SUMMARY")
print("="*80)
print(f"Expected v2 conversations: {len(expected_titles)}")
print(f"Found in database: {len(matched)}")
print(f"Missing: {len(expected_titles) - len(matched)}")

# Check for expected conversation structure from JSON
print("\n" + "="*80)
print("EXPECTED CONVERSATION STRUCTURE (from JSON)")
print("="*80)
for i, conv_data in enumerate(v2_conversations, 1):
    print(f"\n{i}. {conv_data['title']}")
    print(f"   Function: {conv_data['function']}")
    print(f"   Expected turns: {conv_data['expected_turns']}")
    print(f"   User messages in JSON: {len(conv_data['user_messages'])}")
    print(f"   Assistant messages in JSON: {len(conv_data['assistant_messages'])}")

