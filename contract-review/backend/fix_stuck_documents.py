#!/usr/bin/env python3
"""
Fix stuck documents that are in 'pending' status
Triggers processing for all documents with processing_status = 'pending'
"""
import requests
import os
from dotenv import load_dotenv
from database import get_supabase

load_dotenv()

def fix_stuck_documents():
    """Find and trigger processing for all pending documents"""
    supabase = get_supabase()

    # Find all documents stuck in 'pending' status
    result = supabase.table('documents')\
        .select('id, filename, uploaded_by')\
        .eq('processing_status', 'pending')\
        .execute()

    pending_docs = result.data

    if not pending_docs:
        print("✅ No stuck documents found!")
        return

    print(f"📋 Found {len(pending_docs)} stuck document(s):")
    for doc in pending_docs:
        print(f"   - {doc['filename']} (ID: {doc['id']})")

    print("\n🔄 Triggering processing...")

    # Use local backend to trigger processing
    backend_url = "http://localhost:8000"

    for doc in pending_docs:
        try:
            # Get a user token for this user
            user_result = supabase.table('users')\
                .select('id, email')\
                .eq('id', doc['uploaded_by'])\
                .single()\
                .execute()

            if not user_result.data:
                print(f"   ❌ User not found for document {doc['filename']}")
                continue

            user = user_result.data

            # Generate a temporary token for this user
            import jwt
            from datetime import datetime, timedelta

            payload = {
                'sub': user['id'],
                'email': user['email'],
                'aud': 'authenticated',
                'role': 'authenticated',
                'iat': int(datetime.utcnow().timestamp()),
                'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }

            token = jwt.encode(payload, os.getenv('SUPABASE_JWT_SECRET'), algorithm='HS256')

            # Trigger processing
            response = requests.post(
                f"{backend_url}/api/documents/{doc['id']}/process",
                headers={'Authorization': f'Bearer {token}'}
            )

            if response.status_code == 200:
                print(f"   ✅ Processing started for: {doc['filename']}")
            else:
                print(f"   ❌ Failed to process {doc['filename']}: {response.text}")

        except Exception as e:
            print(f"   ❌ Error processing {doc['filename']}: {e}")

    print("\n✅ Done! Check document statuses in a few moments.")

if __name__ == "__main__":
    fix_stuck_documents()
