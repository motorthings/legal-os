-- Migration: 009_help_system.sql
-- Agentic help system — vector-embedded docs + RAG chat
-- Ported from AESOP help system architecture

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. help_documents — source markdown files
CREATE TABLE IF NOT EXISTS help_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'general',
    role_access TEXT[] NOT NULL DEFAULT ARRAY['user', 'admin'],
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_help_documents_category ON help_documents(category);

-- 2. help_chunks — embedded chunks for vector search
CREATE TABLE IF NOT EXISTS help_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES help_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(512),
    chunk_index INTEGER NOT NULL DEFAULT 0,
    heading_context TEXT,
    role_access TEXT[] NOT NULL DEFAULT ARRAY['user', 'admin'],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_help_chunks_document ON help_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_help_chunks_embedding ON help_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);

-- 3. help_conversations — user chat sessions
CREATE TABLE IF NOT EXISTS help_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT NOT NULL DEFAULT 'Help Chat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_help_conversations_user ON help_conversations(user_id);

-- 4. help_messages — messages within conversations
CREATE TABLE IF NOT EXISTS help_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES help_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    feedback INTEGER DEFAULT NULL CHECK (feedback IN (-1, 0, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_help_messages_conversation ON help_messages(conversation_id);

-- 5. match_help_chunks — vector similarity search RPC
CREATE OR REPLACE FUNCTION match_help_chunks(
    query_embedding VECTOR(512),
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5,
    filter_roles TEXT[] DEFAULT ARRAY['user']
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    heading_context TEXT,
    similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_file_path TEXT
)
LANGUAGE plpgsql
SET search_path = 'public'
AS $$
BEGIN
    RETURN QUERY
    SELECT
        hc.id,
        hc.document_id,
        hc.content,
        hc.heading_context,
        1 - (hc.embedding <=> query_embedding) AS similarity,
        hc.metadata,
        hd.title AS document_title,
        hd.file_path AS document_file_path
    FROM help_chunks hc
    JOIN help_documents hd ON hd.id = hc.document_id
    WHERE 1 - (hc.embedding <=> query_embedding) > match_threshold
      AND hc.role_access && filter_roles
    ORDER BY hc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 6. RLS — service role full access, authenticated users read docs + own conversations
ALTER TABLE help_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE help_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE help_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE help_messages ENABLE ROW LEVEL SECURITY;

-- Service role bypass for all
CREATE POLICY "Service role full access on help_documents"
    ON help_documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on help_chunks"
    ON help_chunks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on help_conversations"
    ON help_conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on help_messages"
    ON help_messages FOR ALL USING (true) WITH CHECK (true);
