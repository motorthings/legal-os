#!/usr/bin/env python3
"""
Schedule new interview and inject synthetic transcript
Now that client_id fix is deployed, this will trigger full workflow:
Interview → Stage 1 (TRIPS) → Stage 2 (System Instructions) ✅
"""
import requests
import sys
import json

backend_url = "https://superassistant-mvp-production.up.railway.app"

# Charlie Motor's user ID (from previous session)
charlie_user_id = "d07ac04e-f4f5-439a-a107-ad28e9fa2612"

print("🎬 Schedule New Interview + Inject Synthetic Transcript")
print(f"   User: Charlie Motor (motorthings@gmail.com)")
print(f"   User ID: {charlie_user_id}")
print()

# Step 1: Check backend is ready
print("1️⃣ Checking backend status...")
try:
    response = requests.get(f"{backend_url}/health", timeout=10)
    if response.status_code == 200:
        print("   ✅ Backend online")
    else:
        print(f"   ⚠️  Backend returned {response.status_code}")
except Exception as e:
    print(f"   ❌ Backend unreachable: {e}")
    sys.exit(1)

print()
print("⚠️  You'll need to schedule the interview via the admin UI first:")
print(f"   1. Go to: {backend_url.replace('superassistant-mvp-production.up.railway.app', 'your-frontend-url')}/admin/users/{charlie_user_id}")
print("   2. Click 'Schedule Interview'")
print("   3. Wait for session to be created")
print("   4. Then run: python inject_via_webhook.py")
print()
print("OR - if you already scheduled a new interview, just run:")
print("   python inject_via_webhook.py")
print()

proceed = input("Have you scheduled a new interview? (y/N): ").strip().lower()

if proceed == 'y':
    print()
    print("📤 Injecting synthetic transcript...")
    import inject_via_webhook
    result = inject_via_webhook.inject_interview(backend_url)

    if result:
        print()
        print("🎉 SUCCESS! Check the output above for:")
        print("   ✅ Extraction ID")
        print("   ✅ Solomon Stage 1 status (TRIPS extraction)")
        print("   ✅ Solomon Stage 2 status (System instructions)")
        print()
        print("If Stage 2 succeeded, you now have:")
        print("   - Personalized system instructions in solomon_reviews table")
        print("   - Ready to test the chat interface!")
        sys.exit(0)
    else:
        sys.exit(1)
else:
    print()
    print("Please schedule a new interview first, then run this script again!")
    sys.exit(0)
