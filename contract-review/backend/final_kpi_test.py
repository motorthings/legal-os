import requests
from datetime import datetime, timedelta

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"

headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

# Get all conversations for Charlie (past 30 days)
now = datetime.utcnow()
start_date = now - timedelta(days=30)

url = f"{SUPABASE_URL}/rest/v1/conversations"
params = {
    "user_id": f"eq.{CHARLIE_USER_ID}",
    "select": "id,title,created_at",
    "gte": f"created_at.{start_date.isoformat()}",
    "order": "created_at.desc"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    conversations = response.json()
    print(f"✅ Total conversations (past 30 days): {len(conversations)}\n")
    
    # Check strategic keywords
    strategic_keywords = [
        'conceptual', 'model', 'framework', 'strategy',
        'plan', 'draft', 'report', 'brief', 'memo'
    ]
    
    strategic_count = 0
    unique_convos = set()
    
    # Get all messages for these conversations
    conversation_ids = [c['id'] for c in conversations]
    
    msgs_url = f"{SUPABASE_URL}/rest/v1/messages"
    msgs_params = {
        "select": "id,conversation_id,role,content,timestamp",
        "eq": "role.user",
        "order": "timestamp.asc"
    }
    
    # Query messages in batches
    all_strategic_convos = set()
    
    for conv in conversations:
        conv_id = conv['id']
        
        # Get first user message for this conversation
        msg_params = {
            "conversation_id": f"eq.{conv_id}",
            "role": "eq.user",
            "select": "content",
            "order": "timestamp.asc",
            "limit": "1"
        }
        
        msg_response = requests.get(msgs_url, headers=headers, params=msg_params)
        
        if msg_response.status_code == 200 and msg_response.json():
            first_msg = msg_response.json()[0]
            content_lower = first_msg['content'].lower()
            
            # Check for keywords
            has_keyword = any(kw in content_lower for kw in strategic_keywords)
            
            if has_keyword:
                all_strategic_convos.add(conv_id)
    
    print(f"📊 KPI Metrics:")
    print(f"  Total conversations (30 days): {len(conversations)}")
    print(f"  Strategic conversations: {len(all_strategic_convos)}")
    print(f"  Ideation Velocity: {len(all_strategic_convos):.1f} drafts/month")
    print(f"  Weekly average: {len(all_strategic_convos) * 7 / 30:.1f} drafts/week")
    print()
    
    # Calculate Correction Loop
    total_turns = 0
    convo_count = 0
    
    for conv_id in all_strategic_convos:
        # Count user messages in this conversation
        turn_params = {
            "conversation_id": f"eq.{conv_id}",
            "role": "eq.user",
            "select": "id"
        }
        
        turn_response = requests.get(msgs_url, headers=headers, params=turn_params)
        
        if turn_response.status_code == 200:
            num_turns = len(turn_response.json())
            total_turns += num_turns
            convo_count += 1
    
    if convo_count > 0:
        avg_turns = total_turns / convo_count
        print(f"🔄 Correction Loop Efficiency:")
        print(f"  Average turns: {avg_turns:.1f} (goal: <2)")
        print(f"  Status: {'✅ MET' if avg_turns < 2 else '⚠️ NEEDS IMPROVEMENT'}")
    
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
