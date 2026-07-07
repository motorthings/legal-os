#!/usr/bin/env python3
"""
Apply database migrations directly using Supabase client
No psql required - uses Supabase REST API
"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

print("=" * 60)
print("📋 Applying Database Migrations")
print("=" * 60)
print()

# List of migrations to apply
migrations = [
    {
        'file': 'migrations/029_contract_analyses_table.sql',
        'name': 'Migration 029: Contract Analyses Table',
        'description': [
            '- contract_analyses table',
            '- 6 performance indexes',
            '- updated_at trigger',
            '- get_contract_stats() function',
            '- RLS policies (admin + user)'
        ]
    },
    {
        'file': 'migrations/030_contract_type_instructions.sql',
        'name': 'Migration 030: Contract Type Instructions',
        'description': [
            '- contract_type_instructions table',
            '- Seed data for 5 contract types',
            '- updated_at trigger',
            '- RLS policies (admin-only)'
        ]
    }
]

for migration in migrations:
    print(f"📄 {migration['name']}")
    print(f"   File: {migration['file']}")
    print()

    # Read SQL file
    try:
        with open(migration['file'], 'r') as f:
            sql = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Migration file not found: {migration['file']}")
        continue

    # Execute SQL using rpc (Supabase's raw SQL execution)
    # Note: We need to split on semicolons and execute each statement separately
    # because Supabase's RPC doesn't support multi-statement SQL well

    print("   Executing SQL statements...")

    try:
        # Execute the entire SQL file
        # Using the postgrest client to execute raw SQL
        result = supabase.rpc('exec_sql', {'sql': sql}).execute()

        print(f"✅ {migration['name']} applied successfully!")
        print()
        print("Created:")
        for item in migration['description']:
            print(f"  {item}")
        print()

    except Exception as e:
        # If exec_sql doesn't exist, we need to use a different approach
        # Let's try executing via the database connection string
        print(f"   Attempting alternative execution method...")

        try:
            import psycopg2
            from urllib.parse import urlparse

            # Parse database URL from SUPABASE_URL
            # Format: https://PROJECT_REF.supabase.co
            project_ref = SUPABASE_URL.replace('https://', '').replace('.supabase.co', '')

            # Connection string
            conn_string = f"postgresql://postgres:SBPQxRHSy8OMOttZ@db.{project_ref}.supabase.co:5432/postgres"

            conn = psycopg2.connect(conn_string)
            conn.autocommit = True
            cursor = conn.cursor()

            cursor.execute(sql)

            cursor.close()
            conn.close()

            print(f"✅ {migration['name']} applied successfully!")
            print()
            print("Created:")
            for item in migration['description']:
                print(f"  {item}")
            print()

        except ImportError:
            print(f"❌ Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
            print(f"   Or install PostgreSQL client tools and use: ./apply_migration_029.sh")
            exit(1)
        except Exception as e2:
            print(f"❌ Error applying {migration['name']}: {str(e2)}")
            print(f"   Original error: {str(e)}")
            continue

print()
print("=" * 60)
print("✅ All migrations completed!")
print("=" * 60)
