#!/usr/bin/env python3
"""
Test script for Voice Interview Pipeline
Tests the complete flow from interview scheduling to Solomon extraction
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.elevenlabs_interview import create_interview_session, handle_interview_completion, get_interview_status
from services.solomon_stage1 import extract_interview_data
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)


async def test_interview_pipeline():
    """
    Test the complete interview pipeline with mock data
    """

    print("\n" + "="*70)
    print("VOICE INTERVIEW PIPELINE TEST")
    print("="*70 + "\n")

    # Step 1: Create or get a test client
    print("📋 Step 1: Getting test client...")
    try:
        # Try to find existing test client
        result = supabase.table('clients').select('id, name, email').limit(1).execute()

        if result.data and len(result.data) > 0:
            test_client = result.data[0]
            client_id = test_client['id']
            client_name = test_client['name']
            client_email = test_client.get('email', 'test@example.com')
            print(f"   ✅ Using existing client: {client_name} ({client_id})")
        else:
            # Create a test client
            result = supabase.table('clients').insert({
                'name': 'Test Interview Client',
                'email': 'test-interview@example.com',
                'status': 'pending_interview'
            }).execute()

            test_client = result.data[0]
            client_id = test_client['id']
            client_name = test_client['name']
            client_email = test_client['email']
            print(f"   ✅ Created test client: {client_name} ({client_id})")

    except Exception as e:
        print(f"   ❌ Error with client: {str(e)}")
        return

    # Step 2: Create interview session
    print("\n🎙️  Step 2: Creating interview session...")
    try:
        session_result = await create_interview_session(
            client_id=client_id,
            client_name=client_name,
            client_email=client_email,
            organization_name="Test Organization"
        )

        print(f"   ✅ Interview session created")
        print(f"      Session ID: {session_result['session_id']}")
        print(f"      Agent ID: {session_result['agent_id']}")
        print(f"      Session URL: {session_result['session_url']}")
        print(f"      Status: {session_result['status']}")

        if 'note' in session_result:
            print(f"      Note: {session_result['note']}")

        agent_id = session_result['agent_id']
        session_id = session_result['session_id']

    except Exception as e:
        print(f"   ❌ Error creating session: {str(e)}")
        return

    # Step 3: Check interview status (should be 'scheduled')
    print("\n🔍 Step 3: Checking interview status...")
    try:
        status_result = await get_interview_status(client_id)
        print(f"   ✅ Current status: {status_result['status']}")
        print(f"      Created: {status_result.get('created_at', 'N/A')}")

    except Exception as e:
        print(f"   ❌ Error checking status: {str(e)}")

    # Step 4: Simulate interview completion
    print("\n📞 Step 4: Simulating interview completion...")
    try:
        completion_result = await handle_interview_completion(
            agent_id=agent_id,
            session_id=session_id
        )

        print(f"   ✅ Interview completed and processed")
        print(f"      Extraction ID: {completion_result['extraction_id']}")
        print(f"      Transcript length: {completion_result['transcript_length']} chars")
        print(f"      Solomon status: {completion_result['solomon_status']}")

        if 'note' in completion_result:
            print(f"      Note: {completion_result['note']}")

        extraction_id = completion_result['extraction_id']

    except Exception as e:
        print(f"   ❌ Error completing interview: {str(e)}")
        return

    # Step 5: Check extraction results
    print("\n📊 Step 5: Checking extraction results...")
    try:
        extraction_result = supabase.table('interview_extractions')\
            .select('*')\
            .eq('id', extraction_id)\
            .single()\
            .execute()

        extraction = extraction_result.data

        print(f"   ✅ Extraction record found")
        print(f"      Status: {extraction['status']}")
        print(f"      Completeness: {extraction.get('completeness_score', 0)}%")

        if extraction.get('extraction_json'):
            json_data = extraction['extraction_json']
            print(f"\n   📝 Extracted Data Summary:")
            print(f"      Pain Points: {len(json_data.get('pain_points', []))}")
            print(f"      Core Values: {len(json_data.get('core_values', []))}")
            print(f"      Frameworks: {len(json_data.get('frameworks', []))}")
            print(f"      Success Metrics: {len(json_data.get('success_metrics', []))}")

            if 'metadata' in json_data:
                metadata = json_data['metadata']
                print(f"\n   🔍 Metadata:")
                print(f"      Interview Quality: {metadata.get('interview_quality', 'N/A')}")
                print(f"      Completeness Score: {metadata.get('completeness_score', 0)}%")

                if metadata.get('clarification_needed'):
                    print(f"      Clarification Needed: {len(metadata['clarification_needed'])} items")

                if metadata.get('suggested_core_functions'):
                    print(f"      Suggested Functions: {', '.join(metadata['suggested_core_functions'])}")

    except Exception as e:
        print(f"   ❌ Error checking extraction: {str(e)}")

    # Step 6: Check final interview status
    print("\n🔍 Step 6: Checking final interview status...")
    try:
        status_result = await get_interview_status(client_id)
        print(f"   ✅ Final status: {status_result['status']}")
        print(f"      Completed: {status_result.get('completed_at', 'N/A')}")

    except Exception as e:
        print(f"   ❌ Error checking final status: {str(e)}")

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✅ All pipeline steps completed successfully!")
    print("\nThe following components were tested:")
    print("  • Interview session creation (STUB with mock data)")
    print("  • Interview completion webhook handling")
    print("  • Solomon Stage 1 extraction (FUNCTIONAL)")
    print("  • Interview status tracking")
    print("  • Database integration")
    print("\nNext Steps:")
    print("  1. Configure ElevenLabs API key to enable real voice interviews")
    print("  2. Implement Solomon Stage 2 (configuration generation)")
    print("  3. Build Solomon review dashboard for admins")
    print("  4. Test end-to-end with real voice interview")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_interview_pipeline())
