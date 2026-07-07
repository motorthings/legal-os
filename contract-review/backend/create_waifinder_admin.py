#!/usr/bin/env python3
"""
Create admin user charlie@waifinder.org for Contentful contract review demo
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

ADMIN_EMAIL = "charlie@waifinder.org"
ADMIN_PASSWORD = "ButtButt"
ADMIN_NAME = "Charlie Fuller"

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

try:
    print(f"Creating admin user: {ADMIN_EMAIL}")

    # Create user in Supabase Auth
    auth_response = supabase.auth.admin.create_user({
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "email_confirm": True,
        "user_metadata": {
            "name": ADMIN_NAME
        }
    })

    user_id = auth_response.user.id
    print(f"✅ Created auth user with ID: {user_id}")

    # Create user record in users table
    user_record = supabase.table('users').insert({
        'id': user_id,
        'email': ADMIN_EMAIL,
        'name': ADMIN_NAME,
        'role': 'admin',
        'client_id': '00000000-0000-0000-0000-000000000001'
    }).execute()

    print(f"✅ Created user record in users table")
    print(f"")
    print(f"🎉 Admin user created successfully!")
    print(f"   Email: {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"   Role: admin")

except Exception as e:
    if "already been registered" in str(e) or "duplicate key" in str(e):
        print(f"ℹ️  User {ADMIN_EMAIL} already exists!")
    else:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
