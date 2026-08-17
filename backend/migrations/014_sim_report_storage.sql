-- Store the generated report and the resume checkpoint in Postgres so run output
-- survives machine restarts without a persistent volume.
alter table public.runs add column if not exists report text;
alter table public.runs add column if not exists mc_checkpoint jsonb;
