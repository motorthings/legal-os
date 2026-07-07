#!/usr/bin/env python3
"""
Cleanup script for contract review demo
- Removes all documents and related data (chunks, analyses)
- Removes Paige user accounts
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("=" * 60)
print("🧹 Contract Review Demo Cleanup")
print("=" * 60)
print()

# Step 1: Delete all document chunks
print("1. Deleting document chunks...")
try:
    chunks_result = supabase.table('document_chunks').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    chunks_deleted = len(chunks_result.data) if chunks_result.data else 0
    print(f"   ✅ Deleted {chunks_deleted} document chunks")
except Exception as e:
    print(f"   ⚠️  Error deleting chunks: {str(e)}")

# Step 2: Delete all contract analyses
print("2. Deleting contract analyses...")
try:
    analyses_result = supabase.table('contract_analysis').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    analyses_deleted = len(analyses_result.data) if analyses_result.data else 0
    print(f"   ✅ Deleted {analyses_deleted} contract analyses")
except Exception as e:
    print(f"   ⚠️  Error deleting analyses: {str(e)}")

# Step 3: Get all documents to delete from storage
print("3. Fetching documents for storage cleanup...")
try:
    docs_result = supabase.table('documents').select('id, storage_path, filename').execute()
    documents = docs_result.data
    print(f"   Found {len(documents)} documents to clean up")

    # Delete from storage
    if documents:
        print("3. Deleting files from Supabase storage...")
        storage_deleted = 0
        for doc in documents:
            try:
                storage_path = doc.get('storage_path')
                if storage_path:
                    supabase.storage.from_('documents').remove([storage_path])
                    storage_deleted += 1
            except Exception as e:
                # Continue even if storage deletion fails
                pass
        print(f"   ✅ Deleted {storage_deleted} files from storage")

    # Delete from database
    print("3. Deleting document records (continued)...")
    supabase.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print(f"   ✅ Deleted {len(documents)} document records")

except Exception as e:
    print(f"   ⚠️  Error with documents: {str(e)}")

# Step 4: Delete all conversations and messages
print("4. Deleting conversations and messages...")
try:
    # Delete messages first (foreign key constraint)
    messages_result = supabase.table('messages').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    messages_deleted = len(messages_result.data) if messages_result.data else 0
    print(f"   ✅ Deleted {messages_deleted} messages")

    # Delete conversations
    conversations_result = supabase.table('conversations').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    conversations_deleted = len(conversations_result.data) if conversations_result.data else 0
    print(f"   ✅ Deleted {conversations_deleted} conversations")

except Exception as e:
    print(f"   ⚠️  Error deleting conversations: {str(e)}")

# Step 5: Delete Paige users
print("5. Removing Paige users...")
try:
    # Find Paige users
    paige_users = supabase.table('users').select('id, email').ilike('email', '%paige%').execute()

    if paige_users.data:
        for user in paige_users.data:
            user_id = user['id']
            email = user['email']

            print(f"   Removing user: {email}")

            # Delete from users table
            supabase.table('users').delete().eq('id', user_id).execute()

            # Delete from auth (this will cascade delete related data)
            try:
                supabase.auth.admin.delete_user(user_id)
                print(f"   ✅ Deleted user: {email}")
            except Exception as e:
                print(f"   ⚠️  Could not delete auth user {email}: {str(e)}")
    else:
        print("   ℹ️  No Paige users found")

except Exception as e:
    print(f"   ⚠️  Error removing Paige users: {str(e)}")

print()
print("=" * 60)
print("✅ Cleanup complete!")
print("=" * 60)
print()
print("Remaining demo users:")
print("  - charlie@sickofancy.ai / ButtButt")
print("  - charlie@waifinder.org / ButtButt")
print()
print("Database is ready for fresh contract uploads!")
