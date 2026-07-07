import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

# Get recent conversations
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
    "limit": 15
}

conv_response = requests.get(conv_url, headers=headers, params=params)
conversations = conv_response.json()

print(f"📊 Checking messages for {len(conversations)} conversations\n")
print("="*80)

for i, conv in enumerate(conversations[:10], 1):
    # Get messages for this conversation
    msg_url = f"{SUPABASE_URL}/rest/v1/messages"
    msg_params = {
        "conversation_id": f"eq.{conv['id']}",
        "select": "role,content,timestamp",
        "order": "timestamp.asc"
    }
    
    msg_response = requests.get(msg_url, headers=headers, params=msg_params)
    messages = msg_response.json()
    
    print(f"\n{i}. {conv['title']}")
    print(f"   Created: {conv['created_at'][:10]}")
    print(f"   Messages: {len(messages)}")
    
    if len(messages) > 0:
        print(f"   First message preview:")
        first_msg = messages[0]
        content_preview = first_msg['content'][:150] + "..." if len(first_msg['content']) > 150 else first_msg['content']
        print(f"      [{first_msg['role']}] {content_preview}")
        
        if len(messages) > 1:
            print(f"   Last message preview:")
            last_msg = messages[-1]
            content_preview = last_msg['content'][:150] + "..." if len(last_msg['content']) > 150 else last_msg['content']
            print(f"      [{last_msg['role']}] {content_preview}")
    else:
        print(f"   ⚠️  NO MESSAGES FOUND")
    
    print("-"*80)

print("\n✅ Check complete")
