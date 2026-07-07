# Database Migrations

This directory contains SQL migrations for the SuperAssistant MVP database.

## How to Apply Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of the migration file
4. Paste and execute the SQL

### Option 2: Supabase CLI

```bash
supabase db push
```

## Migrations

### 021_recalculate_storage_used.sql

**Date:** 2025-11-16
**Purpose:** Recalculate storage_used for all users to fix incorrect values caused by double increment/decrement bug

**Changes:**
- Runs `recalculate_all_user_storage()` function to fix all user storage values
- Corrects negative or incorrect storage_used values

**Problem Solved:**
- Fixed double increment/decrement bug where storage_used was being updated both by database trigger AND application code
- This caused storage_used to go negative, violating the `chk_storage_used_positive` constraint
- Users were unable to delete documents due to this constraint violation

**Run with:**
```bash
cd backend
python3 run_migration_021.py
```

Or apply manually in Supabase SQL Editor.

### 020_fix_vector_search.sql

**Date:** 2025-11-16
**Purpose:** Fix vector search by creating missing RPC function and correcting vector dimensions

**CRITICAL FIX:** This migration resolves the issue where knowledge base searches were failing silently.

**Changes:**
- Enables pgvector extension for vector similarity search
- Fixes embedding column dimensions: 1536 → 1024 (to match Voyage AI voyage-3 model)
- Creates missing `match_document_chunks()` PostgreSQL function
- Adds HNSW index for fast vector similarity search
- Adds helper function to validate embedding quality

**Problem Solved:**
- Knowledge base searches were failing with "function not found" error
- `match_document_chunks()` RPC function was being called but didn't exist
- Vector dimensions were inconsistent with the embedding model
- No indexes existed for efficient vector search

**IMPORTANT NOTES:**
1. **Backup your database before running this migration**
2. If you have existing embeddings with wrong dimensions (1536), you may need to:
   - Delete existing chunks: `DELETE FROM document_chunks;`
   - Reprocess all documents via `/api/documents/{id}/process`
3. After migration, test KB search by uploading a text file and querying it

**Apply in Supabase SQL Editor:**
```sql
-- Copy the contents of 020_fix_vector_search.sql and paste into SQL Editor
```

### 019_notion_sync_cadence.sql

**Date:** 2025-11-13
**Purpose:** Add automatic sync scheduling to Notion integration

**Changes:**
- Adds `sync_frequency` column (manual, daily, weekly, monthly)
- Adds `last_auto_sync` timestamp column
- Adds `next_sync_scheduled` timestamp column
- Adds `default_page_ids` array column for default pages to sync
- Creates index for scheduled syncs query

**Problem Solved:**
- Frontend was calling `/api/notion/sync-settings` endpoint which didn't exist
- Users couldn't configure automatic sync frequency for Notion pages
- Enables consistent automatic sync behavior between Google Drive and Notion

**Apply in Supabase SQL Editor or via:**
```bash
supabase db push
```

### 018_fix_storage_external_sources.sql

**Date:** 2025-11-12
**Purpose:** Fix storage calculation to exclude external sources (Google Drive, Notion)

**Changes:**
- Modifies `update_user_storage()` trigger to exclude Google Drive and Notion documents
- Only counts direct uploads towards user storage quota
- Creates `recalculate_all_user_storage()` function to fix existing data
- Recalculates all user storage_used values correctly

**Problem Solved:**
- Fixed `chk_storage_used_positive` constraint violation when deleting external documents
- External documents (Google Drive, Notion) were incorrectly decrementing storage_used
- This caused storage_used to go negative since external docs never counted towards quota

**Run with:**
```bash
cd backend
python3 run_migration_018.py
```

Or apply manually in Supabase SQL Editor.

### 017_add_storage_limits.sql

**Date:** 2025-11-11
**Purpose:** Add storage quota and usage tracking to users

**Changes:**
- Adds `storage_quota` column (default 500MB)
- Adds `storage_used` column
- Creates trigger to automatically update storage on document insert/update/delete
- Adds constraints to prevent negative values

### 002_add_avatar_url_to_users.sql

**Date:** 2025-11-03
**Purpose:** Add profile avatar support for users

**Changes:**
- Adds `avatar_url` column to `users` table
- Creates index on `avatar_url` for performance
- Includes instructions for creating `avatars` storage bucket
- Sets up RLS policies for avatar uploads

**Important Notes:**
1. **Before running this migration**, you must create the `avatars` storage bucket:
   - Go to **Storage** in Supabase dashboard
   - Click **New Bucket**
   - Name it `avatars`
   - Make it **public**
   - Click **Save**

2. **After creating the bucket**, apply the storage policies included in the migration file in the SQL Editor

3. The `avatar_url` column will be `NULL` by default for existing users

**Testing:**
- Test avatar upload via the profile page
- Verify avatars display in UserMenu component
- Test avatar deletion
- Confirm RLS policies work correctly

## Migration Checklist

- [ ] Create `avatars` storage bucket in Supabase dashboard
- [ ] Run migration SQL in Supabase SQL Editor
- [ ] Apply storage RLS policies
- [ ] Test avatar upload functionality
- [ ] Verify avatar display in UI
- [ ] Test avatar deletion
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
