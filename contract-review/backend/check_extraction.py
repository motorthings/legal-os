#!/usr/bin/env python3
"""
Check if interview extraction and TRIPS scores are in database
"""
import requests
import json

backend_url = "https://superassistant-mvp-production.up.railway.app"

print("🔍 Checking for interview extractions...")
print()

try:
    # This endpoint requires admin auth, so let's just check if we can hit the API
    response = requests.get(f"{backend_url}/health", timeout=10)
    print(f"✅ Backend is up: {response.status_code}")
    print()
except Exception as e:
    print(f"❌ Backend check failed: {e}")
    print()

print("To check the database directly, you can:")
print()
print("1. Go to Supabase Dashboard:")
print("   - Navigate to your interview_extractions table")
print("   - Look for the most recent record (sort by created_at DESC)")
print()
print("2. Check these fields:")
print("   - transcript: Should contain the full conversation")
print("   - extraction_data: JSONB field with TRIPS scores")
print("   - status: Should be 'completed' or 'pending_solomon'")
print()
print("3. Expected TRIPS scores in extraction_data:")
print("   {")
print('     "trips": {')
print('       "calendar_management": {')
print('         "time_cost": 85-90,')
print('         "repetition": 85-90,')
print('         "importance": 80-85,')
print('         "pain": 75-80,')
print('         "skill_gap": 60-70')
print('       },')
print('       "coaching_feedback": { ... }')
print('     },')
print('     "pain_points": [...],')
print('     "values": [...],')
print('     "frameworks": [...],')
print('     "team_structure": [...]')
print("   }")
print()
print("4. Or query via SQL in Supabase:")
print("   SELECT id, status, created_at, extraction_data->'trips'")
print("   FROM interview_extractions")
print("   ORDER BY created_at DESC LIMIT 1;")
print()
