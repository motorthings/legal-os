import requests
import json

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Strategic keywords from the KPI code
strategic_keywords = [
    'conceptual', 'model', 'framework', 'strategy',
    'plan', 'draft', 'report', 'brief', 'memo'
]

# Get Charlie's conversations
url = f"{SUPABASE_URL}/rest/v1/conversations"
params = {
    "user_id": f"eq.{CHARLIE_USER_ID}",
    "select": "id,title,created_at",
    "order": "created_at.desc",
    "limit": 15
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    conversations = response.json()
    print(f"✅ Found {len(conversations)} conversations for Charlie\n")
    
    # Check each conversation for strategic keywords
    strategic_count = 0
    
    for conv in conversations[:10]:  # Check our 10 synthetic ones
        print(f"Conversation: {conv['title']}")
        print(f"  Created: {conv['created_at']}")
        
        # Get messages for this conversation
        msgs_url = f"{SUPABASE_URL}/rest/v1/messages"
        msgs_params = {
            "conversation_id": f"eq.{conv['id']}",
            "role": "eq.user",
            "select": "content",
            "order": "timestamp.asc",
            "limit": 1
        }
        
        msgs_response = requests.get(msgs_url, headers=headers, params=msgs_params)
        
        if msgs_response.status_code == 200 and msgs_response.json():
            first_msg = msgs_response.json()[0]
            content_lower = first_msg['content'].lower()
            
            # Check for keywords
            found_keywords = [kw for kw in strategic_keywords if kw in content_lower]
            
            if found_keywords:
                strategic_count += 1
                print(f"  ✅ Strategic keywords found: {', '.join(found_keywords)}")
            else:
                print(f"  ❌ No strategic keywords found")
                print(f"  First message preview: {first_msg['content'][:100]}...")
        else:
            print(f"  ❌ No messages found")
        
        print()
    
    print(f"\n📊 Summary:")
    print(f"  Total conversations: {len(conversations)}")
    print(f"  Strategic conversations: {strategic_count}")
    print(f"  Expected by KPI: {strategic_count}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
