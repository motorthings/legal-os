"""
Test the extraction query to see what error we get
"""
import os
from supabase import create_client
from dotenv import load_dotenv
import traceback

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

extraction_id = '5c615335-e299-43c0-b7d8-408ab7763798'

try:
    print(f"🔍 Querying extraction {extraction_id[:8]}...")

    result = supabase.table('interview_extractions')\
        .select('''
            *,
            clients(id, name, status),
            interview_sessions(
                id,
                agent_id,
                session_id,
                session_url,
                status,
                created_at,
                completed_at,
                metadata
            ),
            solomon_reviews(
                id,
                status,
                generated_instructions,
                reviewed_at,
                reviewed_by,
                deployment_notes,
                deployed_at,
                created_at,
                metadata
            )
        ''')\
        .eq('id', extraction_id)\
        .single()\
        .execute()

    print("✅ Query successful!")
    print(f"\nData keys: {result.data.keys()}")
    print(f"\nInterview session: {result.data.get('interview_sessions')}")
    print(f"\nSolomon reviews: {result.data.get('solomon_reviews')}")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()
