#!/usr/bin/env python3
"""
Re-inject synthetic interview now that client_id fix is deployed
This will create a new extraction with proper client_id and trigger Stage 2
"""
import requests
import sys

backend_url = "https://superassistant-mvp-production.up.railway.app"

print("🔄 Re-injecting Synthetic Interview with Fixed Code")
print()
print("This will:")
print("  1. Use the most recent interview session (should have client_id now)")
print("  2. Inject the synthetic transcript")
print("  3. Trigger Solomon Stage 1 (TRIPS extraction)")
print("  4. Trigger Solomon Stage 2 (System instructions) ✨")
print()

# Check if backend is ready
try:
    response = requests.get(f"{backend_url}/health", timeout=10)
    if response.status_code == 200:
        print("✅ Backend is online")
    else:
        print(f"⚠️  Backend returned {response.status_code}")
except Exception as e:
    print(f"❌ Backend check failed: {e}")
    print()
    sys.exit(1)

print()
print("⚠️  Note: This will create a new extraction record.")
print("   The old extraction (dfbe853e-79c9-4b09-932c-da2e0cc9d1c3) will remain.")
print()

proceed = input("Proceed with re-injection? (y/N): ").strip().lower()

if proceed != 'y':
    print("Cancelled.")
    sys.exit(0)

print()
print("📤 Triggering injection...")
print()

# Import and run the injection
try:
    import inject_via_webhook
    result = inject_via_webhook.inject_interview(backend_url)

    if result:
        print()
        print("🎉 Success! Check the output above for:")
        print("   - New Extraction ID")
        print("   - Solomon Stage 1 status")
        print("   - Solomon Stage 2 status (should succeed this time!)")
        sys.exit(0)
    else:
        print()
        print("❌ Injection failed - check output above")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
