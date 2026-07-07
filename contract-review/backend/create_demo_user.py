#!/usr/bin/env python3
"""
Create demo user for Contentful contract review demo
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

# Demo user credentials
DEMO_EMAIL = "charlie@sickofancy.ai"
DEMO_PASSWORD = "ButtButt"
DEMO_NAME = "Charlie Fuller"

print("🔌 Connecting to Supabase...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print(f"👤 Creating demo user: {DEMO_EMAIL}")

try:
    # Create user in Supabase Auth
    auth_response = supabase.auth.admin.create_user({
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "name": DEMO_NAME
        }
    })

    user_id = auth_response.user.id
    print(f"✅ Created auth user with ID: {user_id}")

    # Check if default client exists
    client_result = supabase.table('clients').select('*').eq('id', '00000000-0000-0000-0000-000000000001').execute()

    if not client_result.data:
        print("  ℹ️  Creating default client...")
        supabase.table('clients').insert({
            'id': '00000000-0000-0000-0000-000000000001',
            'name': 'Default Client'
        }).execute()

    # Create user record in users table
    user_record = supabase.table('users').insert({
        'id': user_id,
        'email': DEMO_EMAIL,
        'name': DEMO_NAME,
        'role': 'admin',  # Make them admin for demo
        'client_id': '00000000-0000-0000-0000-000000000001'
    }).execute()

    print(f"✅ Created user record in users table")

    print("\n🎉 Demo user created successfully!")
    print("\n📋 Login Credentials:")
    print(f"   Email: {DEMO_EMAIL}")
    print(f"   Password: {DEMO_PASSWORD}")
    print("\nYou can now sign in at: https://your-vercel-url.vercel.app/auth/login")

except Exception as e:
    error_msg = str(e)

    if "already been registered" in error_msg or "already exists" in error_msg:
        print(f"ℹ️  User {DEMO_EMAIL} already exists!")
        print("   You can sign in with the existing account.")
    else:
        print(f"❌ Error creating user: {error_msg}")
        sys.exit(1)
