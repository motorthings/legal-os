#!/usr/bin/env python3
"""Quick fix for UUID type cast error in match_document_chunks"""
import os
import sys

# Read the migration SQL
sql = """
-- Drop the existing function with wrong signature
DROP FUNCTION IF EXISTS match_document_chunks(vector(1024), int, text);

-- Recreate with correct UUID type for filter_client_id
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1024),
    match_count int DEFAULT 5,
    filter_client_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    conversation_id uuid,
    client_id uuid,
    content text,
    embedding vector(1024),
    similarity float,
    metadata jsonb,
    source_type text,
    chunk_index int,
    created_at timestamptz
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.conversation_id,
        dc.client_id,
        dc.content,
        dc.embedding,
        (1 - (dc.embedding <=> query_embedding))::float AS similarity,
        dc.metadata,
        dc.source_type,
        dc.chunk_index,
        dc.created_at
    FROM public.document_chunks dc
    WHERE
        (filter_client_id IS NULL OR dc.client_id = filter_client_id)
        AND dc.embedding IS NOT NULL
    ORDER BY
        dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

print("=" * 80)
print("UUID TYPE FIX FOR match_document_chunks")
print("=" * 80)
print("\nThis will fix the error:")
print("  'operator does not exist: uuid = text'")
print("\n" + "=" * 80)

# Try using Supabase client
try:
    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in environment")

    print("\n🔄 Connecting to Supabase...")
    supabase = create_client(supabase_url, supabase_key)

    print("✅ Connected successfully")
    print("\n🔄 Executing SQL fix...")

    # Execute the SQL using RPC or direct query
    result = supabase.rpc('exec_sql', {'sql': sql}).execute()

    print("✅ Migration executed successfully!")
    print("\n" + "=" * 80)
    print("✅ UUID type cast error has been fixed!")
    print("   You can now use knowledge base search without errors.")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Could not apply automatically: {e}")
    print("\nPlease apply this SQL manually in Supabase SQL Editor:")
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Create a new query and paste this SQL:")
    print("\n" + "=" * 80)
    print(sql)
    print("=" * 80)
    print("\n4. Click 'Run' to execute the migration")
    print("\nThis will fix the UUID type error immediately.")
    sys.exit(1)
