"""
Backfill storage_used for all users based on their existing documents
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

print("🔄 Backfilling storage_used for all users...\n")

# Get all users
users_result = client.table('users').select('id, email, storage_used').execute()
users = users_result.data

print(f"Found {len(users)} users\n")

for user in users:
    user_id = user['id']
    email = user['email']
    current_storage_used = user.get('storage_used') or 0

    # Get all documents for this user
    docs_result = client.table('documents')\
        .select('file_size')\
        .eq('uploaded_by', user_id)\
        .execute()

    documents = docs_result.data

    # Calculate total storage used
    total_size = sum(doc.get('file_size', 0) for doc in documents)

    if total_size != current_storage_used:
        # Update user's storage_used
        client.table('users').update({
            'storage_used': total_size
        }).eq('id', user_id).execute()

        print(f"✅ {email}:")
        print(f"   Documents: {len(documents)}")
        print(f"   Previous: {current_storage_used:,} bytes")
        print(f"   Actual: {total_size:,} bytes")
        print(f"   Updated: {total_size:,} bytes\n")
    else:
        print(f"✓ {email}: Already correct ({total_size:,} bytes, {len(documents)} docs)")

print("\n✅ Backfill complete!")
