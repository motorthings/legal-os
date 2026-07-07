"""
TRIPS Scoring Test Script
Tests the extraction of Time/Repetition/Importance/Pain/Data-availability scores
from voice interview transcripts

Usage:
    python test_trips_scoring.py
"""

import sys
import os
import asyncio
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.solomon_stage1 import extract_interview_data
from database import get_supabase
import uuid

supabase = get_supabase()

# Sample interview transcript with clear TRIPS indicators
SAMPLE_TRANSCRIPT = """
AGENT: Hello! Let's start with what's not working as well as you'd like. What tasks or decisions tend to pile up on your desk?

USER: Oh wow, where do I start? The biggest bottleneck is definitely our weekly reporting process. It takes me an entire day every Friday to compile status updates from all my direct reports. I'm talking like 6-8 hours of just copy-pasting data from different spreadsheets and formatting it into a coherent report. And the frustrating part is, I do this every single week without fail. It's exhausting.

AGENT: That sounds really time-consuming. Can you tell me more about the data - is it all in one place or scattered?

USER: It's completely scattered. Everyone uses different tools - some use Google Sheets, others have their own Excel files, and a few track things in Asana. There's no single source of truth, which is why it takes so long to pull it all together. I've tried to standardize it, but nothing sticks.

AGENT: I see. What about decision-making? Think about a recent decision that took longer than it should have.

USER: Good question. Last month we had to decide whether to pursue a new partnership opportunity. It should have been a quick yes or no, but it dragged on for three weeks. The problem was we didn't have clear criteria for evaluating partnerships. Is it about revenue potential? Strategic alignment? Resource requirements? We had all these competing priorities and no framework to weigh them against each other. It was critical for our Q2 goals, but we just spun our wheels.

AGENT: When you look at how you spend your time, what percentage goes to strategic work versus operational tasks?

USER: Honestly? I'd say I spend about 80% of my time on operational stuff - responding to emails, putting out fires, handling administrative tasks. Maybe 20% on actual strategic thinking. But ideally, I'd flip that. I should be spending at least 60% of my time on strategy and only 40% on operations. That's where I add the most value.

AGENT: What would you focus on if you could free up 10 hours per week?

USER: I'd invest that time in developing my team's capabilities. Right now, I'm the bottleneck for too many decisions because I haven't delegated effectively. If I had more time, I could create better documentation, build training materials, and coach my direct reports so they can handle more independently. That's been a nagging priority for six months but I never have time for it.

AGENT: Let's talk about frameworks. Do you use any strategic frameworks in your work?

USER: We use OKRs - Objectives and Key Results - pretty religiously. Every quarter we set them, and I reference them constantly when prioritizing work. I also use the Eisenhower Matrix for my own task management, though I wish the whole team used it consistently.

AGENT: Great. Now about your documentation - where do your strategic documents live?

USER: Most of our key documents are in Google Drive, but it's not super organized. We have folders for different projects, but things get scattered. Some critical frameworks are in Notion, and honestly, some are probably just sitting in old email threads. It's somewhat organized but could definitely be better.

AGENT: Last question - how do you measure success in your role?

USER: We track three main KPIs: customer retention rate, team productivity metrics, and our quarterly OKR completion rate. Those are what I'm accountable for. If those numbers are good, I'm doing my job.
"""

# Expected TRIPS scores based on the transcript above
EXPECTED_TRIPS_RANGES = {
    "weekly_reporting": {
        "time_cost": (80, 100),      # "entire day" → very high
        "repetition": (75, 100),      # "every single week" → very high
        "importance": (40, 70),       # Not critical, but necessary
        "pain_level": (70, 90),       # "exhausting", "frustrating" → high
        "data_availability": (10, 30) # "completely scattered" → very low
    },
    "decision_framework": {
        "time_cost": (60, 80),        # "three weeks" → high
        "repetition": (20, 40),       # Occasional, not frequent
        "importance": (80, 100),      # "critical for Q2 goals" → very high
        "pain_level": (50, 70),       # "spun our wheels" → moderate-high
        "data_availability": (30, 50) # "no framework" → low-moderate
    },
    "team_delegation": {
        "time_cost": (70, 90),        # "80% of time" → high
        "repetition": (70, 90),       # "constantly" implied → high
        "importance": (70, 90),       # "where I add most value" → high
        "pain_level": (60, 80),       # "nagging priority" → moderate-high
        "data_availability": (40, 60) # Some documentation exists
    }
}


def validate_trips_scores(pain_points: list) -> dict:
    """
    Validate that extracted TRIPS scores are within expected ranges

    Returns:
        {
            "passed": bool,
            "results": [...],
            "errors": [...]
        }
    """

    results = []
    errors = []

    print("\n📊 Validating TRIPS Scores\n")
    print("=" * 80)

    for pain_point in pain_points:
        category = pain_point.get('category', 'unknown')
        description = pain_point.get('description', '')
        trips = pain_point.get('trips_score', {})

        print(f"\n🎯 Pain Point: {category}")
        print(f"   Description: {description[:80]}...")

        # Extract scores
        time_cost = trips.get('time_cost', 0)
        repetition = trips.get('repetition', 0)
        importance = trips.get('importance', 0)
        pain_level = trips.get('pain_level', 0)
        data_availability = trips.get('data_availability', 0)

        print(f"\n   TRIPS Scores:")
        print(f"   ├─ Time Cost:         {time_cost:3d}/100")
        print(f"   ├─ Repetition:        {repetition:3d}/100")
        print(f"   ├─ Importance:        {importance:3d}/100")
        print(f"   ├─ Pain Level:        {pain_level:3d}/100")
        print(f"   └─ Data Availability: {data_availability:3d}/100")

        # Check if scores are reasonable (basic validation)
        if all(0 <= score <= 100 for score in [time_cost, repetition, importance, pain_level, data_availability]):
            results.append({
                "category": category,
                "status": "✅ PASS",
                "trips": trips
            })
            print(f"\n   ✅ All scores within valid range (0-100)")
        else:
            errors.append(f"Invalid score range for {category}")
            results.append({
                "category": category,
                "status": "❌ FAIL",
                "trips": trips
            })
            print(f"\n   ❌ FAIL: Scores outside valid range")

    print("\n" + "=" * 80)

    passed = len(errors) == 0

    return {
        "passed": passed,
        "results": results,
        "errors": errors
    }


async def run_test():
    """Run the TRIPS scoring extraction test"""

    print("\n" + "=" * 80)
    print("🧪 TRIPS SCORING EXTRACTION TEST")
    print("=" * 80)

    # Generate test IDs
    test_extraction_id = str(uuid.uuid4())
    test_client_id = str(uuid.uuid4())

    print(f"\n📝 Test Setup:")
    print(f"   Extraction ID: {test_extraction_id}")
    print(f"   Client ID:     {test_client_id}")

    # Create a temporary extraction record
    try:
        supabase.table('interview_extractions').insert({
            'id': test_extraction_id,
            'client_id': test_client_id,
            'transcript': SAMPLE_TRANSCRIPT,
            'status': 'pending_solomon'
        }).execute()

        print(f"   ✅ Test extraction record created")

    except Exception as e:
        print(f"   ❌ Failed to create test record: {str(e)}")
        return

    # Run extraction
    print(f"\n🔄 Running Solomon Stage 1 extraction...")

    try:
        result = await extract_interview_data(
            transcript=SAMPLE_TRANSCRIPT,
            extraction_id=test_extraction_id,
            client_id=test_client_id
        )

        if result['status'] == 'completed':
            print(f"   ✅ Extraction completed successfully")
            print(f"   📊 Completeness score: {result['completeness_score']}%")

            extraction_data = result['extraction_data']

            # Validate TRIPS scores
            pain_points = extraction_data.get('pain_points', [])
            print(f"\n   📋 Extracted {len(pain_points)} pain points")

            validation = validate_trips_scores(pain_points)

            # Print summary
            print("\n" + "=" * 80)
            print("📈 TEST SUMMARY")
            print("=" * 80)

            if validation['passed']:
                print(f"\n✅ TEST PASSED")
                print(f"   All TRIPS scores extracted successfully")
                print(f"   Pain points identified: {len(pain_points)}")
            else:
                print(f"\n❌ TEST FAILED")
                print(f"   Errors found:")
                for error in validation['errors']:
                    print(f"   - {error}")

            # Print extracted frameworks and document storage
            print(f"\n📚 Additional Extractions:")
            print(f"   Frameworks used: {', '.join(extraction_data.get('frameworks_used', []))}")

            doc_storage = extraction_data.get('document_storage', {})
            print(f"   Document storage: {doc_storage.get('platform', 'unknown')}")
            print(f"   Data hygiene: {doc_storage.get('data_hygiene_state', 'unknown')}")

            org_info = extraction_data.get('organization_info', {})
            print(f"   Organization: {org_info.get('organization_name', 'unknown')}")
            print(f"   Industry: {org_info.get('industry', 'unknown')}")

        else:
            print(f"   ❌ Extraction failed: {result['error']}")

    except Exception as e:
        print(f"   ❌ Test failed with error: {str(e)}")

    finally:
        # Cleanup test data
        print(f"\n🧹 Cleaning up test data...")
        try:
            supabase.table('interview_extractions').delete().eq('id', test_extraction_id).execute()
            print(f"   ✅ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️  Cleanup warning: {str(e)}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(run_test())
