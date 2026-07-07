"""
Update all users' storage_quota to 2GB
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

client = create_client(supabase_url, supabase_key)

# 2GB in bytes
TWO_GB = 2 * 1024 * 1024 * 1024  # 2,147,483,648 bytes

print(f"🔄 Updating all users' storage quota to 2GB ({TWO_GB:,} bytes)...\n")

# Get all users
users_result = client.table('users').select('id, email, storage_quota, storage_used').execute()
users = users_result.data

print(f"Found {len(users)} users\n")

for user in users:
    user_id = user['id']
    email = user['email']
    current_quota = user.get('storage_quota') or 0
    storage_used = user.get('storage_used') or 0

    # Calculate usage percentage with new quota
    usage_percentage = (storage_used / TWO_GB) * 100 if TWO_GB > 0 else 0

    # Update user's storage_quota
    client.table('users').update({
        'storage_quota': TWO_GB
    }).eq('id', user_id).execute()

    print(f"✅ {email}:")
    print(f"   Previous quota: {current_quota:,} bytes ({current_quota / (1024**3):.1f} GB)")
    print(f"   New quota: {TWO_GB:,} bytes (2.0 GB)")
    print(f"   Storage used: {storage_used:,} bytes ({storage_used / (1024**2):.2f} MB)")
    print(f"   Usage: {usage_percentage:.2f}%\n")

print("✅ All users updated to 2GB storage quota!")
