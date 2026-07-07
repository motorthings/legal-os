#!/usr/bin/env python3
"""
Fix existing extraction and trigger Solomon Stage 2
Updates client_id and runs Stage 2 to generate system instructions
"""
import requests
import sys

backend_url = "https://superassistant-mvp-production.up.railway.app"
extraction_id = "dfbe853e-79c9-4b09-932c-da2e0cc9d1c3"

print("🔧 Fixing extraction and triggering Solomon Stage 2")
print(f"   Backend: {backend_url}")
print(f"   Extraction ID: {extraction_id}")
print()

# The backend needs to deploy the fix first
print("⚠️  Note: Make sure Railway has finished deploying the client_id fix")
print()
input("Press Enter when ready to continue...")
print()

try:
    # Option 1: Check if there's an API endpoint to trigger Stage 2
    print("1️⃣ Attempting to trigger Stage 2 via API...")

    # First let's check what endpoints are available
    # We may need to create an endpoint or update the extraction directly

    # For now, let's describe what needs to happen:
    print()
    print("📋 What needs to happen:")
    print("   1. Find Charlie Motor's user record in database")
    print("   2. Get their client_id")
    print("   3. Update interview_extractions table:")
    print(f"      UPDATE interview_extractions")
    print(f"      SET client_id = [Charlie's client_id]")
    print(f"      WHERE id = '{extraction_id}';")
    print()
    print("   4. Trigger Solomon Stage 2:")
    print("      - Call generate_system_instructions()")
    print("      - Pass extraction_id and client_id")
    print("      - Generate personalized system instructions")
    print()

    # Let's check if we can do this via the admin panel or need direct DB access
    print("🎯 Recommended approach:")
    print()
    print("Option A: Via Supabase Dashboard (Quick)")
    print("   1. Go to Supabase → Table Editor → users table")
    print("   2. Find Charlie Motor (motorthings@gmail.com)")
    print("   3. Copy his client_id")
    print("   4. Go to interview_extractions table")
    print(f"   5. Find record with id = {extraction_id}")
    print("   6. Update the client_id field with Charlie's client_id")
    print("   7. Update status from 'completed' to 'pending_stage2'")
    print()
    print("Option B: Re-inject Interview (Clean)")
    print("   1. Delete current extraction record")
    print("   2. Schedule new interview (will have correct client_id)")
    print("   3. Run inject_via_webhook.py again")
    print("   4. Stage 2 will run automatically")
    print()

    choice = input("Which option? (A/B or Enter to skip): ").strip().upper()

    if choice == 'B':
        print()
        print("🔄 Re-injecting interview with fixed code...")
        print()

        # Call the injection script
        import inject_via_webhook
        result = inject_via_webhook.inject_interview(backend_url)

        if result:
            print()
            print("✅ Interview re-injected successfully!")
            print("   Solomon Stage 2 should have run automatically")
        else:
            print()
            print("❌ Re-injection failed")
            return False

    elif choice == 'A':
        print()
        print("👍 Manual fix via Supabase Dashboard selected")
        print()
        print("After updating the database:")
        print("   - You may need to manually trigger Stage 2")
        print("   - Or wait for a background job to pick it up")
        print("   - Or create an API endpoint to trigger it")

    return True

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    return False


if __name__ == '__main__':
    result = fix_and_trigger()
    sys.exit(0 if result else 1)
