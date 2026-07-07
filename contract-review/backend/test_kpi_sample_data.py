"""
Sample Data Generator for KPI Testing
Creates realistic test data for Ideation Velocity and Correction Loop KPIs

Usage:
    python test_kpi_sample_data.py --user-id <uuid> --weeks 4

This script generates:
- Conversations with strategic keywords (for Ideation Velocity)
- Messages with varying turn counts (for Correction Loop)
- Realistic timestamps spread across multiple weeks
"""

import sys
import os
from datetime import datetime, timedelta
import random
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase

supabase = get_supabase()

# Strategic keywords for Ideation Velocity testing
STRATEGIC_KEYWORDS = [
    "draft a strategic plan",
    "help me create a conceptual model",
    "build a framework for",
    "develop a strategy for",
    "plan for next quarter",
    "create a report on",
    "design a brief for",
    "outline a memo about"
]

# Non-strategic queries
OPERATIONAL_QUERIES = [
    "what's the status of",
    "can you help me with",
    "I need to know about",
    "quick question about",
    "clarify this for me",
    "explain how",
    "what does this mean",
    "help me understand"
]

# Assistant responses
ASSISTANT_RESPONSES = [
    "I'd be happy to help you with that. Let me start by...",
    "Great question. Based on your strategic priorities...",
    "Here's a framework that might help...",
    "Let me draft that for you...",
    "I've created an initial outline...",
    "That's an excellent use case for the Conceptual_Modeler function..."
]


def generate_test_data(user_id: str, num_weeks: int = 4):
    """
    Generate sample conversations and messages for KPI testing

    Args:
        user_id: UUID of the test user
        num_weeks: Number of weeks to generate data for (default: 4)
    """

    print(f"\n🧪 Generating test data for user: {user_id}")
    print(f"📅 Time period: {num_weeks} weeks")

    # Get user's client_id for validation
    try:
        user_result = supabase.table('users').select('client_id').eq('id', user_id).single().execute()
        if not user_result.data:
            print(f"❌ Error: User {user_id} not found")
            return

        client_id = user_result.data['client_id']
        print(f"✅ Found user (client_id: {client_id})")

    except Exception as e:
        print(f"❌ Error fetching user: {str(e)}")
        return

    # Generate conversations across the time period
    now = datetime.utcnow()
    start_date = now - timedelta(days=num_weeks * 7)

    conversations_created = 0
    strategic_drafts = 0
    operational_convs = 0

    # Generate 2-4 conversations per week
    for week in range(num_weeks):
        num_convs_this_week = random.randint(2, 4)

        for _ in range(num_convs_this_week):
            # Determine if this is a strategic draft or operational conversation
            is_strategic = random.random() < 0.6  # 60% strategic

            # Create conversation
            conv_created_at = start_date + timedelta(
                days=week * 7 + random.randint(0, 6),
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59)
            )

            conv_title = "Test conversation" if not is_strategic else "Strategic planning session"

            try:
                conv_result = supabase.table('conversations').insert({
                    'user_id': user_id,
                    'title': conv_title,
                    'in_knowledge_base': False,
                    'created_at': conv_created_at.isoformat(),
                    'updated_at': conv_created_at.isoformat()
                }).execute()

                conv_id = conv_result.data[0]['id']
                conversations_created += 1

                if is_strategic:
                    strategic_drafts += 1
                else:
                    operational_convs += 1

                # Generate messages for this conversation
                num_turns = random.randint(1, 5)  # 1-5 user turns

                current_time = conv_created_at

                for turn in range(num_turns):
                    # User message
                    if turn == 0:
                        # First message determines strategic vs operational
                        user_content = random.choice(STRATEGIC_KEYWORDS if is_strategic else OPERATIONAL_QUERIES)
                    else:
                        user_content = "Thanks, can you refine that further?" if turn < 3 else "Perfect, that's exactly what I needed."

                    user_msg_time = current_time + timedelta(seconds=random.randint(1, 10))

                    supabase.table('messages').insert({
                        'conversation_id': conv_id,
                        'role': 'user',
                        'content': user_content,
                        'tokens': len(user_content.split()) * 1.3,  # Rough token estimate
                        'created_at': user_msg_time.isoformat()
                    }).execute()

                    # Assistant message
                    assistant_content = random.choice(ASSISTANT_RESPONSES)
                    assistant_msg_time = user_msg_time + timedelta(seconds=random.randint(2, 8))

                    supabase.table('messages').insert({
                        'conversation_id': conv_id,
                        'role': 'assistant',
                        'content': assistant_content,
                        'tokens': len(assistant_content.split()) * 1.3,
                        'created_at': assistant_msg_time.isoformat()
                    }).execute()

                    current_time = assistant_msg_time

            except Exception as e:
                print(f"⚠️  Error creating conversation: {str(e)}")
                continue

    print(f"\n✅ Test data generation complete!")
    print(f"   📊 Total conversations: {conversations_created}")
    print(f"   🎯 Strategic drafts: {strategic_drafts}")
    print(f"   📋 Operational conversations: {operational_convs}")
    print(f"   📈 Expected Ideation Velocity: {strategic_drafts / num_weeks:.1f} drafts/week")

    # Calculate expected correction loop
    print(f"\n📐 To test Correction Loop KPI:")
    print(f"   curl http://localhost:8000/api/kpis/correction-loop")
    print(f"\n📊 To test Ideation Velocity KPI:")
    print(f"   curl http://localhost:8000/api/kpis/ideation-velocity?time_period=month")


def cleanup_test_data(user_id: str):
    """Remove all test conversations for a user"""

    print(f"\n🧹 Cleaning up test data for user: {user_id}")

    try:
        # Get all conversations for this user
        convs_result = supabase.table('conversations').select('id').eq('user_id', user_id).execute()

        conv_ids = [c['id'] for c in convs_result.data]

        if not conv_ids:
            print("No conversations found to clean up.")
            return

        # Delete all messages for these conversations
        supabase.table('messages').delete().in_('conversation_id', conv_ids).execute()

        # Delete all conversations
        supabase.table('conversations').delete().eq('user_id', user_id).execute()

        print(f"✅ Cleaned up {len(conv_ids)} conversations and their messages")

    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate sample KPI test data")
    parser.add_argument('--user-id', required=True, help='User UUID to generate data for')
    parser.add_argument('--weeks', type=int, default=4, help='Number of weeks of data to generate')
    parser.add_argument('--cleanup', action='store_true', help='Clean up existing test data before generating')

    args = parser.parse_args()

    if args.cleanup:
        cleanup_test_data(args.user_id)

    generate_test_data(args.user_id, args.weeks)
