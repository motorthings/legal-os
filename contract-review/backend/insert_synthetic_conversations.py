#!/usr/bin/env python3
"""
Insert synthetic conversations for charlie@sickofancy.ai with realistic date distribution

This script creates 10 synthetic conversations spread across 4 weeks to test
the Bradbury Impact Loop metrics:
- Ideation Velocity: ≥2 drafts/week (strategic conversations)
- Correction Loop Efficiency: <2 turns average

Date Distribution (past 4 weeks):
- Week 1 (oldest): 2 conversations
- Week 2: 3 conversations
- Week 3: 2 conversations
- Week 4 (most recent): 3 conversations

Total: 10 conversations over 4 weeks = 2.5 drafts/week average ✅
"""

import os
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import requests

# Supabase config
SUPABASE_URL = "https://iyugbpnxfbhqjxrvmnij.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml5dWdicG54ZmJocWp4cnZtbmlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTkyODQxMywiZXhwIjoyMDc3NTA0NDEzfQ.X2-uWIFX_LtAREfK8WfODxmXxPjp2MB6g7A-9w42peI"

# Charlie's user info
CHARLIE_USER_ID = "d3ba5354-873a-435a-a36a-853373c4f6e5"
CHARLIE_CLIENT_ID = "4e94bfa4-d02c-4e52-b4d5-f0701f5c320b"
CHARLIE_EMAIL = "charlie@sickofancy.ai"


def create_conversation(title: str, created_at: datetime, user_id: str, client_id: str) -> str:
    """Create a conversation and return its ID (matches real user conversation creation)"""
    url = f"{SUPABASE_URL}/rest/v1/conversations"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    data = {
        "user_id": user_id,
        "client_id": client_id,  # Required for conversations table
        "title": title,
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "in_knowledge_base": False
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 201:
        print(f"❌ Error creating conversation: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()

    result = response.json()
    return result[0]["id"]


def create_message(conversation_id: str, role: str, content: str, timestamp: datetime):
    """Create a message in a conversation (matches real message creation schema)"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }

    # Match actual messages table schema: id, conversation_id, role, content, timestamp
    data = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": timestamp.isoformat()
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 201:
        print(f"❌ Error creating message: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Data: {data}")
        response.raise_for_status()


def main():
    # Load synthetic conversations
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "synthetic_conversations_charlie.json")

    with open(json_path, 'r') as f:
        conversations = json.load(f)

    # Date distribution: Spread 10 conversations across 4 weeks
    # Starting 4 weeks ago (28 days)
    now = datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
    base_date = now - timedelta(days=28)

    # Week distribution: [2, 3, 2, 3] conversations per week
    date_schedule = [
        # Week 1 (28-22 days ago): 2 conversations
        base_date + timedelta(days=1),   # Mon
        base_date + timedelta(days=4),   # Thu

        # Week 2 (21-15 days ago): 3 conversations
        base_date + timedelta(days=8),   # Mon
        base_date + timedelta(days=10),  # Wed
        base_date + timedelta(days=13),  # Sat

        # Week 3 (14-8 days ago): 2 conversations
        base_date + timedelta(days=16),  # Tue
        base_date + timedelta(days=19),  # Fri

        # Week 4 (7-1 days ago): 3 conversations
        base_date + timedelta(days=22),  # Mon
        base_date + timedelta(days=24),  # Wed
        base_date + timedelta(days=26),  # Fri
    ]

    print(f"🚀 Inserting {len(conversations)} synthetic conversations for {CHARLIE_EMAIL}")
    print(f"📅 Date range: {date_schedule[0].strftime('%Y-%m-%d')} to {date_schedule[-1].strftime('%Y-%m-%d')}")
    print(f"📊 Expected Ideation Velocity: {len(conversations)/4:.1f} drafts/week (goal: ≥2)")
    print()

    for idx, conv_data in enumerate(conversations):
        created_at = date_schedule[idx]

        print(f"[{idx+1}/10] Creating conversation: {conv_data['title']}")
        print(f"  Function: {conv_data['function']}")
        print(f"  Date: {created_at.strftime('%Y-%m-%d %A')}")
        print(f"  Expected turns: {conv_data['expected_turns']}")
        print(f"  Strategic keywords: {', '.join(conv_data['strategic_keywords'])}")

        # Create conversation (same as real user conversation creation)
        conversation_id = create_conversation(
            title=conv_data['title'],
            created_at=created_at,
            user_id=CHARLIE_USER_ID,
            client_id=CHARLIE_CLIENT_ID
        )

        print(f"  ✅ Created conversation: {conversation_id}")

        # Create messages (interleave user and assistant messages)
        current_time = created_at
        message_count = 0

        # Interleave messages
        for i in range(max(len(conv_data['user_messages']), len(conv_data['assistant_messages']))):
            # User message
            if i < len(conv_data['user_messages']):
                create_message(
                    conversation_id=conversation_id,
                    role=conv_data['user_messages'][i]['role'],
                    content=conv_data['user_messages'][i]['content'],
                    timestamp=current_time
                )
                message_count += 1
                current_time += timedelta(seconds=30)  # 30 second delay

            # Assistant message
            if i < len(conv_data['assistant_messages']):
                create_message(
                    conversation_id=conversation_id,
                    role=conv_data['assistant_messages'][i]['role'],
                    content=conv_data['assistant_messages'][i]['content'],
                    timestamp=current_time
                )
                message_count += 1
                current_time += timedelta(seconds=60)  # 60 second delay

        print(f"  ✅ Created {message_count} messages")
        print()

    print("✅ All synthetic conversations inserted successfully!")
    print()
    print("📊 Bradbury Impact Loop Test Data:")
    print(f"  - Total conversations: {len(conversations)}")
    print(f"  - Date span: 4 weeks")
    print(f"  - Ideation Velocity: {len(conversations)/4:.1f} drafts/week (goal: ≥2) ✅")
    print(f"  - Average expected turns: {sum(c['expected_turns'] for c in conversations) / len(conversations):.1f} (goal: <2) ✅")
    print()
    print("🔍 Next steps:")
    print("  1. View KPI Dashboard at https://superassistant-mvp.vercel.app/admin")
    print("  2. Check Ideation Velocity card for Charlie")
    print("  3. Check Correction Loop Efficiency card for Charlie")
    print("  4. Verify Usage Analytics shows the conversation trend")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
