"""
Link interview extractions to their interview sessions
Finds extractions without interview_session_id and links them via client_id/metadata
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def link_sessions():
    """Link extractions to sessions based on client_id and timing"""

    print("🔍 Finding unlinked extractions...")

    # Get all extractions without interview_session_id
    extractions = supabase.table('interview_extractions')\
        .select('id, client_id, created_at, interview_session_id')\
        .is_('interview_session_id', 'null')\
        .execute()

    print(f"   Found {len(extractions.data)} extractions without session links")

    if not extractions.data:
        print("✅ All extractions already linked!")
        return

    updates_made = 0

    for extraction in extractions.data:
        print(f"\n📋 Processing extraction {extraction['id'][:8]}...")
        print(f"   Client ID: {extraction['client_id']}")
        print(f"   Created: {extraction['created_at']}")

        # Skip if no client_id
        if not extraction['client_id']:
            print(f"   ⚠️  No client_id - skipping")
            continue

        # Find matching interview session for this client
        # Look for sessions around the same time (within 24 hours)
        sessions = supabase.table('interview_sessions')\
            .select('id, session_id, client_id, created_at, completed_at')\
            .eq('client_id', extraction['client_id'])\
            .execute()

        if not sessions.data:
            print(f"   ⚠️  No interview sessions found for this client")
            continue

        # Find the most recent completed session
        completed_sessions = [s for s in sessions.data if s.get('completed_at')]

        if completed_sessions:
            # Sort by completion time and take the most recent
            completed_sessions.sort(key=lambda s: s['completed_at'], reverse=True)
            session = completed_sessions[0]

            print(f"   ✅ Found matching session: {session['session_id']}")
            print(f"      Completed: {session['completed_at']}")

            # Update extraction with session link
            result = supabase.table('interview_extractions')\
                .update({'interview_session_id': session['id']})\
                .eq('id', extraction['id'])\
                .execute()

            print(f"   ✅ Linked extraction to session")
            updates_made += 1
        else:
            print(f"   ⚠️  No completed sessions found for this client")

    print(f"\n{'='*60}")
    print(f"✅ Completed! Linked {updates_made} extractions to sessions")
    print(f"{'='*60}")

if __name__ == '__main__':
    link_sessions()
