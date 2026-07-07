-- ============================================================================
-- KNOWLEDGE BASE COMPREHENSIVE DIAGNOSTICS (SQL ONLY)
-- Run this entire script in Supabase SQL Editor
-- ============================================================================

-- TEST 1: Check pgvector extension
-- ============================================================================
SELECT 'TEST 1: PGVECTOR EXTENSION' as test;
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
-- Expected: 1 row showing 'vector' extension

-- TEST 2: Check Documents
-- ============================================================================
SELECT 'TEST 2: DOCUMENTS TABLE' as test;
SELECT COUNT(*) as total_documents FROM documents;
SELECT COUNT(*) as processed_documents FROM documents WHERE processed = true;
SELECT
    id,
    filename,
    processed,
    chunk_count,
    source_platform,
    created_at
FROM documents
ORDER BY created_at DESC
LIMIT 10;

-- TEST 3: Check Document Chunks
-- ============================================================================
SELECT 'TEST 3: DOCUMENT CHUNKS TABLE' as test;
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    COUNT(DISTINCT document_id) as unique_documents,
    COUNT(DISTINCT client_id) as unique_clients
FROM document_chunks;

-- TEST 4: Check Embedding Dimensions
-- ============================================================================
SELECT 'TEST 4: EMBEDDING DIMENSIONS' as test;
SELECT
    id,
    document_id,
    array_length(embedding::real[], 1) as dimension,
    length(content) as content_length
FROM document_chunks
WHERE embedding IS NOT NULL
LIMIT 5;
-- Expected: dimension should be 1024

-- TEST 5: Check Content Quality (Sample)
-- ============================================================================
SELECT 'TEST 5: CONTENT QUALITY SAMPLE' as test;
SELECT
    id,
    document_id,
    source_type,
    length(content) as content_length,
    substring(content, 1, 100) as content_preview
FROM document_chunks
LIMIT 5;

-- TEST 6: Verify match_document_chunks Function
-- ============================================================================
SELECT 'TEST 6: FUNCTION SIGNATURE CHECK' as test;
SELECT
    proname as function_name,
    pg_get_function_arguments(oid) as arguments,
    pg_get_function_result(oid) as return_type
FROM pg_proc
WHERE proname = 'match_document_chunks';
-- Expected: filter_client_id should be 'uuid' NOT 'text'

-- TEST 7: Test match_document_chunks with Real Data
-- ============================================================================
SELECT 'TEST 7: FUNCTION EXECUTION TEST' as test;
DO $$
DECLARE
    test_embedding vector(1024);
    result_count int;
BEGIN
    -- Get a sample embedding
    SELECT embedding INTO test_embedding
    FROM document_chunks
    WHERE embedding IS NOT NULL
    LIMIT 1;

    IF test_embedding IS NULL THEN
        RAISE NOTICE 'NO EMBEDDINGS FOUND - Cannot test function';
    ELSE
        -- Test the function
        SELECT COUNT(*) INTO result_count
        FROM match_document_chunks(test_embedding, 5);

        RAISE NOTICE 'Function returned % results', result_count;

        IF result_count = 0 THEN
            RAISE WARNING 'Function returned 0 results - check client_id filtering';
        END IF;
    END IF;
END $$;

-- TEST 8: Show Actual Search Results
-- ============================================================================
SELECT 'TEST 8: SAMPLE SEARCH RESULTS' as test;
WITH sample_embedding AS (
    SELECT embedding
    FROM document_chunks
    WHERE embedding IS NOT NULL
    LIMIT 1
)
SELECT
    id,
    document_id,
    client_id,
    source_type,
    similarity,
    substring(content, 1, 100) as content_preview
FROM match_document_chunks(
    (SELECT embedding FROM sample_embedding),
    5
)
ORDER BY similarity DESC;

-- TEST 9: Check Client ID Distribution
-- ============================================================================
SELECT 'TEST 9: CLIENT ID DISTRIBUTION' as test;
SELECT
    client_id,
    COUNT(*) as chunk_count,
    COUNT(DISTINCT document_id) as document_count
FROM document_chunks
GROUP BY client_id;

-- TEST 10: Identify Potential Issues
-- ============================================================================
SELECT 'TEST 10: DIAGNOSTIC SUMMARY' as test;
SELECT
    'Total Documents' as metric,
    COUNT(*)::text as value
FROM documents
UNION ALL
SELECT
    'Processed Documents',
    COUNT(*)::text
FROM documents
WHERE processed = true
UNION ALL
SELECT
    'Total Chunks',
    COUNT(*)::text
FROM document_chunks
UNION ALL
SELECT
    'Chunks with Embeddings',
    COUNT(*)::text
FROM document_chunks
WHERE embedding IS NOT NULL
UNION ALL
SELECT
    'Unique Client IDs',
    COUNT(DISTINCT client_id)::text
FROM document_chunks
UNION ALL
SELECT
    'Average Chunk Length',
    AVG(length(content))::int::text
FROM document_chunks;

-- ============================================================================
-- TROUBLESHOOTING QUERIES
-- ============================================================================

-- If function signature shows TEXT instead of UUID, run this:
-- DROP FUNCTION IF EXISTS match_document_chunks(vector(1024), int, text);
-- CREATE OR REPLACE FUNCTION match_document_chunks(...) -- See UUID_FIX_INSTRUCTIONS.md

-- If no chunks found:
-- Check: SELECT * FROM documents WHERE processed = false;
-- Then process them via API: POST /api/documents/{id}/process

-- If chunks exist but no embeddings:
-- Check dimension mismatch: SELECT DISTINCT array_length(embedding::real[], 1) FROM document_chunks WHERE embedding IS NOT NULL;

-- If search returns 0 results but embeddings exist:
-- Check client filtering: SELECT DISTINCT client_id FROM document_chunks;
-- Compare with user's client_id from: SELECT id, client_id FROM users;
