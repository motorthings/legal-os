# Migration Execution Order

## Issue
Multiple migrations shared the same sequence numbers, creating ambiguity in execution order.

## Resolution
Migrations have been documented with their correct execution order below. Original filenames are preserved but should be executed in the order listed.

## Correct Execution Order

| Order | Filename | Description |
|-------|----------|-------------|
| 002 | 002_add_avatar_url_to_users.sql | Add profile avatar support |
| 003 | 003_add_document_management_fields.sql | Document management fields |
| 004 | 004_voice_interview_tables.sql | Voice interview tables (original) |
| 005 | 005_add_extraction_prompt.sql | Add extraction prompt support |
| 006 | 006_solomon_review_fields.sql | Solomon review fields |
| 007 | 007_add_organization_and_system_instructions.sql | Organization and system instructions |
| 008 | 004_voice_interview_tables_FIXED.sql | Voice interview tables (fixed version) |
| 009 | 009_user_level_document_isolation.sql | User-level document isolation |
| 010 | 010_conversation_knowledge_base.sql | Conversation knowledge base |
| 011 | 011_google_drive_integration.sql | Google Drive integration |
| 012 | 012_google_drive_sync_cadence.sql | Google Drive sync scheduling |
| 013 | 013_oauth_states_table.sql | OAuth states table |
| 014 | 014_add_document_sync_cadence.sql | Document sync cadence |
| 015 | 015_conversation_archive.sql | Conversation archive |
| 016 | 016_conversation_search.sql | Conversation search |
| 017 | 017_add_storage_limits.sql | Storage quota tracking |
| 018 | 018_fix_storage_external_sources.sql | Fix storage calculation (MUST RUN FIRST of 018s) |
| 019 | 019_notion_sync_cadence.sql | Notion sync scheduling |
| 020 | 020_fix_vector_search.sql | Fix vector search (MUST RUN FIRST of 020s) |
| 021 | 021_recalculate_storage_used.sql | Recalculate storage (MUST RUN FIRST of 021s) |
| 022 | 022_fix_uuid_type_cast.sql | Fix UUID type casting |
| 023 | 023_add_missing_indexes.sql | Add performance indexes (MUST RUN FIRST of 023s) |
| 024 | 024_system_instruction_document_mappings.sql | System instruction mappings |
| 025 | 025_user_quick_prompts.sql | User quick prompts (MUST RUN FIRST of 025s) |
| 026 | 026_add_function_tags.sql | Add function tags |
| 027 | 027_drop_alignment_documents.sql | Drop alignment documents (MUST RUN FIRST of 027s) |
| 028 | 015_notion_integration.sql | Notion integration |
| 029 | 018_add_provider_to_oauth_states.sql | Add provider to OAuth states |
| 030 | 018_user_prompts_auto_generation.sql | User prompts auto-generation |
| 031 | 020_add_mime_type_column.sql | Add MIME type column |
| 032 | 021_fix_postgrest_schema_cache.sql | Fix PostgREST schema cache |
| 033 | 023_add_core_document_flag.sql | Add core document flag |
| 034 | 025_add_approval_fields_to_extractions.sql | Add approval fields to extractions |
| 035 | 027_add_useable_output_tracking.sql | Add useable output tracking |
| 036 | add_performance_indexes.sql | Additional performance indexes |

## Notes

### Critical Dependencies

1. **Storage Migrations (018, 021):** Must run 018_fix_storage_external_sources.sql before 021_recalculate_storage_used.sql
2. **Vector Search (020):** Must run 020_fix_vector_search.sql before other 020 migrations
3. **Quick Prompts (025):** Must run 025_user_quick_prompts.sql before 025_add_approval_fields_to_extractions.sql

### Duplicate Number Groups

**004 Group:**
- 004_voice_interview_tables.sql (original implementation)
- 004_voice_interview_tables_FIXED.sql (bug fixes for above)
- Recommendation: Run both in order

**015 Group:**
- 015_conversation_archive.sql (conversation archiving)
- 015_notion_integration.sql (Notion integration - independent)
- Recommendation: Run conversation_archive first

**018 Group:**
- 018_fix_storage_external_sources.sql (fixes storage bug) - **RUN FIRST**
- 018_add_provider_to_oauth_states.sql (adds OAuth provider field)
- 018_user_prompts_auto_generation.sql (user prompts feature)

**020 Group:**
- 020_fix_vector_search.sql (fixes KB search) - **RUN FIRST**
- 020_add_mime_type_column.sql (adds MIME type tracking)

**021 Group:**
- 021_recalculate_storage_used.sql (depends on 018 fix) - **RUN FIRST**
- 021_fix_postgrest_schema_cache.sql (PostgREST cache fix)

**023 Group:**
- 023_add_missing_indexes.sql (performance indexes) - **RUN FIRST**
- 023_add_core_document_flag.sql (core document tracking)

**025 Group:**
- 025_user_quick_prompts.sql (quick prompts table) - **RUN FIRST**
- 025_add_approval_fields_to_extractions.sql (extraction approval)

**027 Group:**
- 027_drop_alignment_documents.sql (removes old table) - **RUN FIRST**
- 027_add_useable_output_tracking.sql (output tracking)

## Future Migrations

Going forward, use sequential numbering starting from **037**.

## Verification

After running migrations, verify with:

```sql
-- Check all tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Check critical indexes
SELECT indexname FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY indexname;

-- Verify vector search function
SELECT proname FROM pg_proc
WHERE proname = 'match_document_chunks';
```

## Rollback Strategy

Each migration should be tested in a staging environment before production.
Critical migrations (storage, vector search) have specific rollback procedures documented in their files.
