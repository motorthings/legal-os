-- ============================================================================
-- Legal AI OS — Legal Research: raw result payload
-- ============================================================================
-- Store the full Descrybe case object (court, authority label, treatment
-- category, why-relevant note, etc.) so cached results can be reconstructed
-- with the same richness as fresh results.
-- ============================================================================

alter table legal_research_results
    add column if not exists raw jsonb not null default '{}';
