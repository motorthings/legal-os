-- Separate, named, saved reports per run — one row per stage, keyed by run.
--
-- Before this, a run had a single `runs.report` column that both the baseline pass and
-- the lever optimization wrote to, so the second stage clobbered the first and the UI
-- could not tell which report it was showing. This table keeps every stage's report:
--
--   baseline             — the firm as-is, nothing changed (the starting line)
--   lever_optimization   — the adaptive search: which levers to pull, in what order
--   scenario_simulation  — a determined lever set run through a fresh Monte Carlo
--                          (repeatable: one row per re-run)
--
-- `payload` carries the `optimize` dict the report was built from, so a scenario re-run
-- can reuse the optimization's narrative and only refresh the confidence band.
create table if not exists public.sim_reports (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.runs(id) on delete cascade,
  stage text not null check (stage in ('baseline', 'lever_optimization', 'scenario_simulation')),
  title text not null,
  lever_set jsonb not null default '[]'::jsonb,
  payload jsonb,
  report_markdown text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_sim_reports_run on public.sim_reports (run_id, created_at desc);
