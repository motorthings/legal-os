-- Phase 4 — report regeneration. Stores the exact inputs a report was rendered from
-- (meta + metrics + experiments, incl. the sensitivity bands and model variance) so the
-- report can be RE-RENDERED from stored data without re-running the simulation. Changing
-- the report format then costs nothing to regenerate.

alter table public.sim_reports add column if not exists render_inputs jsonb;
