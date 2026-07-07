import requests

SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

conv_url = f"{SUPABASE_URL}/rest/v1/conversations"
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

params = {
    "user_id": "eq.d3ba5354-873a-435a-a36a-853373c4f6e5",
    "select": "id,title,created_at,is_archived,in_knowledge_base",
    "order": "created_at.desc",
    "limit": 20
}

response = requests.get(conv_url, headers=headers, params=params)
conversations = response.json()

print("Conversation Archive/KB Status:")
print("="*80)
for conv in conversations:
    archived = conv.get('is_archived', False)
    in_kb = conv.get('in_knowledge_base', False)
    status = []
    if archived:
        status.append("ARCHIVED")
    if in_kb:
        status.append("IN_KB")
    if not status:
        status.append("ACTIVE")
    
    print(f"{conv['title'][:50]:50} {' '.join(status):15} {conv['created_at'][:10]}")

print("\n" + "="*80)
archived_count = sum(1 for c in conversations if c.get('is_archived', False))
kb_count = sum(1 for c in conversations if c.get('in_knowledge_base', False))
active_count = sum(1 for c in conversations if not c.get('is_archived', False))

print(f"Total: {len(conversations)}")
print(f"Active: {active_count}")
print(f"Archived: {archived_count}")
print(f"In Knowledge Base: {kb_count}")

