#!/usr/bin/env python3
"""
Apply migration 007 - Add organization and system_instructions columns
This script uses direct database connection to execute DDL statements
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Try using psycopg2 for direct database connection
try:
    import psycopg2
    from urllib.parse import urlparse

    # Get database URL from environment (Supabase provides this)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

    if not db_url:
        print("❌ No DATABASE_URL found. Please run this SQL manually in Supabase SQL Editor:")
        print("""
        -- Add organization and system_instructions columns to clients table
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS organization TEXT;
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS system_instructions TEXT;
        COMMENT ON COLUMN clients.organization IS 'Client organization name, used for customizing system instructions';
        COMMENT ON COLUMN clients.system_instructions IS 'Generated system instructions from Solomon Stage 2';
        """)
        sys.exit(1)

    print("📊 Applying migration 007: Add organization and system_instructions columns")
    print("=" * 70)

    # Connect to database
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Execute migration statements
    statements = [
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS organization TEXT;",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS system_instructions TEXT;",
        "COMMENT ON COLUMN clients.organization IS 'Client organization name, used for customizing system instructions';",
        "COMMENT ON COLUMN clients.system_instructions IS 'Generated system instructions from Solomon Stage 2';"
    ]

    for stmt in statements:
        print(f"Executing: {stmt[:60]}...")
        cur.execute(stmt)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Migration applied successfully!")
    print("=" * 70)

except ImportError:
    print("⚠️  psycopg2 not available. Please apply this SQL manually in Supabase:")
    print("""
    -- Add organization and system_instructions columns to clients table
    ALTER TABLE clients ADD COLUMN IF NOT EXISTS organization TEXT;
    ALTER TABLE clients ADD COLUMN IF NOT EXISTS system_instructions TEXT;
    COMMENT ON COLUMN clients.organization IS 'Client organization name, used for customizing system instructions';
    COMMENT ON COLUMN clients.system_instructions IS 'Generated system instructions from Solomon Stage 2';
    """)
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease apply this SQL manually in Supabase SQL Editor:")
    print("""
    -- Add organization and system_instructions columns to clients table
    ALTER TABLE clients ADD COLUMN IF NOT EXISTS organization TEXT;
    ALTER TABLE clients ADD COLUMN IF NOT EXISTS system_instructions TEXT;
    COMMENT ON COLUMN clients.organization IS 'Client organization name, used for customizing system instructions';
    COMMENT ON COLUMN clients.system_instructions IS 'Generated system instructions from Solomon Stage 2';
    """)
    sys.exit(1)
