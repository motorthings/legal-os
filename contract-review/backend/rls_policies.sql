-- ============================================
-- SuperAssistant MVP - Row Level Security Policies
-- ============================================
-- This file contains RLS policies for multi-tenant data isolation
-- Run these commands in Supabase SQL Editor
-- Date: November 2, 2025
-- ============================================

-- ============================================
-- 1. DOCUMENTS TABLE POLICIES
-- ============================================

-- Enable RLS on documents table
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view documents from their own client
CREATE POLICY "users_view_own_client_documents"
ON public.documents
FOR SELECT
TO authenticated
USING (
  client_id IN (
    SELECT client_id
    FROM public.users
    WHERE id = auth.uid()
  )
);

-- Policy: Admins can view all documents
CREATE POLICY "admins_view_all_documents"
ON public.documents
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Users can upload documents to their client
CREATE POLICY "users_upload_to_own_client"
ON public.documents
FOR INSERT
TO authenticated
WITH CHECK (
  client_id IN (
    SELECT client_id
    FROM public.users
    WHERE id = auth.uid()
  )
);

-- Policy: Admins can insert documents anywhere
CREATE POLICY "admins_insert_documents"
ON public.documents
FOR INSERT
TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Users can update documents in their client
CREATE POLICY "users_update_own_client_documents"
ON public.documents
FOR UPDATE
TO authenticated
USING (
  client_id IN (
    SELECT client_id
    FROM public.users
    WHERE id = auth.uid()
  )
);

-- Policy: Users can delete documents in their client
CREATE POLICY "users_delete_own_client_documents"
ON public.documents
FOR DELETE
TO authenticated
USING (
  client_id IN (
    SELECT client_id
    FROM public.users
    WHERE id = auth.uid()
  )
);


-- ============================================
-- 2. CONVERSATIONS TABLE POLICIES
-- ============================================

-- Enable RLS on conversations table
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own conversations
CREATE POLICY "users_view_own_conversations"
ON public.conversations
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- Policy: Admins can view all conversations
CREATE POLICY "admins_view_all_conversations"
ON public.conversations
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Users can create their own conversations
CREATE POLICY "users_create_conversations"
ON public.conversations
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- Policy: Users can update their own conversations
CREATE POLICY "users_update_own_conversations"
ON public.conversations
FOR UPDATE
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- Policy: Users can delete their own conversations
CREATE POLICY "users_delete_own_conversations"
ON public.conversations
FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- Policy: Admins can manage all conversations
CREATE POLICY "admins_manage_all_conversations"
ON public.conversations
FOR ALL
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);


-- ============================================
-- 3. MESSAGES TABLE POLICIES
-- ============================================

-- Enable RLS on messages table
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view messages from their own conversations
CREATE POLICY "users_view_own_messages"
ON public.messages
FOR SELECT
TO authenticated
USING (
  conversation_id IN (
    SELECT id
    FROM public.conversations
    WHERE user_id = auth.uid()
  )
);

-- Policy: Admins can view all messages
CREATE POLICY "admins_view_all_messages"
ON public.messages
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Users can insert messages in their own conversations
CREATE POLICY "users_create_messages_in_own_conversations"
ON public.messages
FOR INSERT
TO authenticated
WITH CHECK (
  conversation_id IN (
    SELECT id
    FROM public.conversations
    WHERE user_id = auth.uid()
  )
);

-- Policy: Users can update messages in their own conversations
CREATE POLICY "users_update_own_messages"
ON public.messages
FOR UPDATE
TO authenticated
USING (
  conversation_id IN (
    SELECT id
    FROM public.conversations
    WHERE user_id = auth.uid()
  )
);

-- Policy: Users can delete messages in their own conversations
CREATE POLICY "users_delete_own_messages"
ON public.messages
FOR DELETE
TO authenticated
USING (
  conversation_id IN (
    SELECT id
    FROM public.conversations
    WHERE user_id = auth.uid()
  )
);


-- ============================================
-- 4. DOCUMENT_CHUNKS TABLE POLICIES
-- ============================================

-- Enable RLS on document_chunks table
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view chunks from documents in their client
CREATE POLICY "users_view_own_client_chunks"
ON public.document_chunks
FOR SELECT
TO authenticated
USING (
  document_id IN (
    SELECT id
    FROM public.documents
    WHERE client_id IN (
      SELECT client_id
      FROM public.users
      WHERE id = auth.uid()
    )
  )
);

-- Policy: Admins can view all chunks
CREATE POLICY "admins_view_all_chunks"
ON public.document_chunks
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Users can insert chunks for documents in their client
CREATE POLICY "users_insert_chunks_for_own_client"
ON public.document_chunks
FOR INSERT
TO authenticated
WITH CHECK (
  document_id IN (
    SELECT id
    FROM public.documents
    WHERE client_id IN (
      SELECT client_id
      FROM public.users
      WHERE id = auth.uid()
    )
  )
);


-- ============================================
-- 5. CLIENTS TABLE POLICIES (Already have from Day 3)
-- ============================================

-- Verify clients table has RLS enabled (should already be done)
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own client
CREATE POLICY "users_view_own_client"
ON public.clients
FOR SELECT
TO authenticated
USING (
  id IN (
    SELECT client_id
    FROM public.users
    WHERE id = auth.uid()
  )
);

-- Policy: Admins can view all clients
CREATE POLICY "admins_view_all_clients"
ON public.clients
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);

-- Policy: Admins can manage all clients
CREATE POLICY "admins_manage_clients"
ON public.clients
FOR ALL
TO authenticated
USING (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = auth.uid()
    AND role IN ('admin', 'client_admin')
  )
);


-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these to verify policies are working correctly

-- Check which policies exist on each table
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Check RLS status on tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('users', 'clients', 'documents', 'document_chunks', 'conversations', 'messages');

-- ============================================
-- NOTES
-- ============================================
-- 1. These policies ensure multi-tenant data isolation
-- 2. Regular users can only access data for their own client
-- 3. Admins and client_admins have full access to all data
-- 4. Service role bypasses all RLS (used by backend API)
-- 5. Test thoroughly with different user roles before production!
-- ============================================
