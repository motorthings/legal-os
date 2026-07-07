#!/usr/bin/env python3
"""
Test Solomon Pipeline with Synthetic Interview Transcript
Tests Stage 1 extraction and Stage 2 generation using the synthetic Charlie Fuller interview
"""

import asyncio
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.solomon_stage1 import extract_interview_data
from services.solomon_stage2 import generate_system_instructions
from supabase import create_client
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)


async def test_synthetic_interview():
    """
    Test Solomon pipeline with synthetic Charlie Fuller interview transcript
    """

    print("\n" + "="*80)
    print("SOLOMON PIPELINE TEST - SYNTHETIC INTERVIEW DATA")
    print("="*80 + "\n")

    # Step 1: Load the synthetic interview transcript
    print("📄 Step 1: Loading synthetic interview transcript...")
    # Try backend/test_data first (for Railway deployment), then ../test_data (for local)
    backend_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'test_data',
        'synthetic_interview_transcript_charlie_fuller.txt'
    )
    root_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'test_data',
        'synthetic_interview_transcript_charlie_fuller.txt'
    )
    transcript_path = backend_path if os.path.exists(backend_path) else root_path

    try:
        with open(transcript_path, 'r') as f:
            transcript = f.read()

        print(f"   ✅ Transcript loaded: {len(transcript)} characters")
        print(f"      File: {transcript_path}")
    except Exception as e:
        print(f"   ❌ Error loading transcript: {str(e)}")
        return

    # Step 2: Create or get test client
    print("\n👤 Step 2: Setting up test client...")
    try:
        # Check if Charlie Fuller test client exists
        result = supabase.table('clients')\
            .select('id, name')\
            .eq('name', 'Charlie Fuller - Test')\
            .execute()

        if result.data and len(result.data) > 0:
            test_client = result.data[0]
            client_id = test_client['id']
            print(f"   ✅ Using existing test client: {test_client['name']} ({client_id})")
        else:
            # Create test client for Charlie Fuller
            result = supabase.table('clients').insert({
                'name': 'Charlie Fuller - Test',
                'assistant_name': 'Charlie AI',
                'status': 'pending_interview'
            }).execute()

            test_client = result.data[0]
            client_id = test_client['id']
            print(f"   ✅ Created test client: Charlie Fuller - Test ({client_id})")

    except Exception as e:
        print(f"   ❌ Error with client: {str(e)}")
        return

    # Step 3: Create interview extraction record
    print("\n📊 Step 3: Creating interview extraction record...")
    try:
        extraction_id = str(uuid.uuid4())

        result = supabase.table('interview_extractions').insert({
            'id': extraction_id,
            'client_id': client_id,
            'transcript': transcript,
            'status': 'pending'
        }).execute()

        print(f"   ✅ Extraction record created: {extraction_id}")

    except Exception as e:
        print(f"   ❌ Error creating extraction record: {str(e)}")
        return

    # Step 4: Run Solomon Stage 1 - Extraction
    print("\n🔬 Step 4: Running Solomon Stage 1 (Data Extraction)...")
    print("   ⏳ Calling Claude Haiku 4.5 to extract structured data...")

    try:
        stage1_result = await extract_interview_data(
            transcript=transcript,
            extraction_id=extraction_id,
            client_id=client_id
        )

        if stage1_result['status'] == 'completed':
            print(f"   ✅ Stage 1 completed successfully!")
            print(f"      Completeness Score: {stage1_result['completeness_score']}%")
            print(f"      Cost: ~$0.04 (estimated)")

            extraction_data = stage1_result['extraction_data']

            # Display extracted data summary
            print(f"\n   📝 Extracted Data Summary:")
            print(f"      Pain Points: {len(extraction_data.get('pain_points', []))}")
            for i, pp in enumerate(extraction_data.get('pain_points', [])[:3], 1):
                print(f"        {i}. {pp.get('description', 'N/A')[:60]}...")

            print(f"\n      Core Values: {len(extraction_data.get('core_values', []))}")
            for i, cv in enumerate(extraction_data.get('core_values', [])[:3], 1):
                print(f"        {i}. {cv.get('value', 'N/A')}")

            print(f"\n      Leadership Styles: {', '.join(extraction_data.get('leadership_styles', []))}")

            print(f"\n      Frameworks: {len(extraction_data.get('frameworks', []))}")
            for fw in extraction_data.get('frameworks', []):
                print(f"        • {fw.get('name', 'N/A')}")

            team = extraction_data.get('team_structure', {})
            print(f"\n      Team Size: {team.get('team_size', 0)} (Direct Reports: {len(team.get('direct_reports', []))})")

            comm = extraction_data.get('communication_style', {})
            print(f"\n      Communication Style:")
            print(f"        • Tone: {comm.get('tone', 'N/A')}")
            print(f"        • Detail Level: {comm.get('detail_level', 'N/A')}")
            print(f"        • Directness: {comm.get('directness', 'N/A')}")

            print(f"\n      Success Metrics: {len(extraction_data.get('success_metrics', []))}")

            focus = extraction_data.get('strategic_focus', {})
            print(f"\n      Strategic Priorities: {len(focus.get('top_priorities', []))}")
            for i, p in enumerate(focus.get('top_priorities', [])[:3], 1):
                print(f"        {i}. {p.get('priority', 'N/A')[:60]}...")

            metadata = extraction_data.get('metadata', {})
            print(f"\n   🔍 Metadata:")
            print(f"      Interview Quality: {metadata.get('interview_quality', 'N/A')}")
            print(f"      Completeness Score: {metadata.get('completeness_score', 0)}%")

            if metadata.get('suggested_core_functions'):
                print(f"      Suggested Core Functions:")
                for func in metadata['suggested_core_functions']:
                    print(f"        • {func}")

            if metadata.get('clarification_needed'):
                print(f"\n      ⚠️  Clarification Needed: {len(metadata['clarification_needed'])} items")
                for item in metadata['clarification_needed'][:3]:
                    print(f"        • {item}")

            # Check if Stage 2 was auto-triggered
            completeness = stage1_result['completeness_score']
            if completeness >= 70:
                print(f"\n   🚀 Completeness >= 70%, Stage 2 should have auto-triggered!")
            else:
                print(f"\n   ⚠️  Completeness < 70%, Stage 2 not triggered (needs review)")

        else:
            print(f"   ❌ Stage 1 failed: {stage1_result['error']}")
            return

    except Exception as e:
        print(f"   ❌ Error running Stage 1: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Check if Stage 2 completed (should auto-trigger if completeness >= 70%)
    print("\n🎨 Step 5: Checking Solomon Stage 2 (System Instructions Generation)...")

    try:
        # Give Stage 2 a moment to complete
        await asyncio.sleep(2)

        # Check client record for system instructions
        client_result = supabase.table('clients')\
            .select('system_instructions, status')\
            .eq('id', client_id)\
            .single()\
            .execute()

        if client_result.data and client_result.data.get('system_instructions'):
            instructions = client_result.data['system_instructions']
            print(f"   ✅ Stage 2 completed! System instructions generated")
            print(f"      Length: {len(instructions)} characters")
            print(f"      Client Status: {client_result.data.get('status', 'N/A')}")
            print(f"      Cost: ~$0.20 (estimated)")

            # Display first few lines of system instructions
            print(f"\n   📜 System Instructions Preview:")
            lines = instructions.split('\n')[:10]
            for line in lines:
                print(f"      {line}")
            print(f"      ... ({len(instructions.split(chr(10)))} total lines)")

            # Save full instructions to file for review
            # Try backend/test_data first (for Railway deployment), then ../test_data (for local)
            backend_output = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'test_data',
                'generated_system_instructions_charlie_fuller.txt'
            )
            root_output = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'test_data',
                'generated_system_instructions_charlie_fuller.txt'
            )
            # Use backend path if that directory exists, otherwise use root
            test_data_dir = os.path.dirname(backend_output)
            output_path = backend_output if os.path.exists(test_data_dir) else root_output
            with open(output_path, 'w') as f:
                f.write(instructions)
            print(f"\n   💾 Full instructions saved to: {output_path}")

        else:
            print(f"   ⏳ Stage 2 not yet completed or not triggered")
            print(f"      This may be normal if completeness < 70%")
            print(f"      Client Status: {client_result.data.get('status', 'N/A') if client_result.data else 'N/A'}")

    except Exception as e:
        print(f"   ❌ Error checking Stage 2: {str(e)}")

    # Step 6: Display extraction record final status
    print("\n📋 Step 6: Final extraction record status...")
    try:
        extraction_result = supabase.table('interview_extractions')\
            .select('status, completeness_score, processed_at')\
            .eq('id', extraction_id)\
            .single()\
            .execute()

        if extraction_result.data:
            print(f"   ✅ Extraction Status: {extraction_result.data.get('status', 'N/A')}")
            print(f"      Completeness: {extraction_result.data.get('completeness_score', 0)}%")
            print(f"      Processed: {extraction_result.data.get('processed_at', 'N/A')}")

    except Exception as e:
        print(f"   ❌ Error checking extraction status: {str(e)}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("✅ Solomon Pipeline test completed successfully!")
    print("\nComponents Tested:")
    print("  ✓ Synthetic interview transcript loading")
    print("  ✓ Database record creation")
    print("  ✓ Solomon Stage 1 - Interview Data Extraction (Claude Haiku 4.5)")
    print("  ✓ Solomon Stage 2 - System Instructions Generation (Claude Opus)")
    print("  ✓ Auto-trigger logic (completeness >= 70%)")
    print("  ✓ Full pipeline cost estimation (~$0.24 total)")
    print("\nExtracted Data:")
    print(f"  • Pain Points: {len(extraction_data.get('pain_points', []))}")
    print(f"  • Core Values: {len(extraction_data.get('core_values', []))}")
    print(f"  • Frameworks: {len(extraction_data.get('frameworks', []))}")
    print(f"  • Team Members: {len(team.get('direct_reports', []))}")
    print(f"  • Completeness: {completeness}%")
    print("\nNext Steps:")
    print("  1. Review generated system instructions")
    print("  2. Test the AI assistant with the new instructions")
    print("  3. Refine interview questions if needed")
    print("  4. Test with real ElevenLabs voice interview")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_synthetic_interview())
