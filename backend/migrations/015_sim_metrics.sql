-- Store the primary seed's per-sprint metric trajectories so the frontend can render
-- the sprint-by-sprint charts without depending on the ephemeral run artifacts on disk.
alter table public.runs add column if not exists metrics jsonb;
