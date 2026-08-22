-- Phase 3 — model variance. Stores the LLM's own uncertainty envelope for a run, measured
-- by re-running the same firm at different sampling temperatures. Separate from the seed-level
-- MC band (structural/process variance): this is the spread the MODEL adds on top. Mock runs
-- store {"mode":"deterministic","count":0} — the model gave the same answer every time.

alter table public.runs add column if not exists model_variance jsonb;
