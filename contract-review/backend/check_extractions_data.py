#!/usr/bin/env python3
"""
Check if interview extractions exist and what data they have
"""
import requests
import json

backend_url = "https://superassistant-mvp-production.up.railway.app"

print("🔍 Checking Interview Extractions Data")
print("=" * 70)
print()

# Check 1: Test the API endpoint directly
print("1️⃣ Testing API endpoint: GET /api/extractions")
print()

try:
    # Note: This will fail without auth, but we can see the error
    response = requests.get(f"{backend_url}/api/extractions", timeout=10)
    print(f"   Status: {response.status_code}")

    if response.status_code == 401:
        print("   ⚠️  Authentication required (expected)")
        print("   Need to call this endpoint as authenticated admin")
    elif response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success!")
        print(f"   Extractions found: {len(data.get('data', []))}")
        print()
        print("   Data:")
        print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"   ❌ Unexpected status: {response.text[:500]}")

except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print()
print("=" * 70)
print()

# Instructions for checking database directly
print("2️⃣ Check Database Directly in Supabase:")
print()
print("   Run this SQL query:")
print()
print("   SELECT ")
print("     ie.id,")
print("     ie.client_id,")
print("     ie.status,")
print("     ie.completeness_score,")
print("     ie.created_at,")
print("     c.name as client_name,")
print("     sr.status as review_status,")
print("     sr.generated_instructions IS NOT NULL as has_instructions")
print("   FROM interview_extractions ie")
print("   LEFT JOIN clients c ON ie.client_id = c.id")
print("   LEFT JOIN solomon_reviews sr ON sr.extraction_id = ie.id")
print("   ORDER BY ie.created_at DESC;")
print()
print("=" * 70)
print()

# Check if the issue is the relationship
print("3️⃣ Possible Issues:")
print()
print("   Issue A: Railway hasn't deployed yet")
print("     - Wait 2-3 more minutes")
print("     - Check Railway dashboard for deployment status")
print()
print("   Issue B: Foreign key relationship not set up")
print("     - interview_extractions.client_id → clients.id")
print("     - solomon_reviews.extraction_id → interview_extractions.id")
print()
print("   Issue C: No client_id in extraction")
print("     - Check: SELECT client_id FROM interview_extractions;")
print("     - Should NOT be NULL")
print()
print("   Issue D: Frontend API call failing")
print("     - Open browser console (F12)")
print("     - Look for errors in Network tab")
print("     - Check /api/extractions call")
print()

print("=" * 70)
print()
print("What to do:")
print("1. Check browser console (F12) → Network tab")
print("2. Look for the /api/extractions request")
print("3. Check if it's 200 OK or an error")
print("4. If error, paste the error message")
