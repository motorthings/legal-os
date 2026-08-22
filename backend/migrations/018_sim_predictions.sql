-- Phase 4 — back-test / validation. The model's predictions, the firm's actuals, and the
-- gap between them. This is what turns "plausible" into "proven": each prediction carries
-- a point value AND a band, so once a real outcome is recorded we can measure both the error
-- and whether the band covered reality. Written by the runner/service via the service role.

create table if not exists public.prediction_records (
  id              uuid primary key default gen_random_uuid(),
  firm_id         uuid references public.firms (id) on delete set null,
  run_id          uuid references public.runs (id) on delete set null,
  metric          text not null default 'ppp',     -- what was predicted (ppp, margin, ...)
  predicted_value double precision not null,       -- the point prediction
  band_low        double precision,                -- the honest range, not a point
  band_high       double precision,
  horizon_sprints int,                             -- the horizon the prediction is about
  config_hash     text,                            -- replay hash — bind prediction to its inputs
  created_at      timestamptz not null default now()
);
create index if not exists prediction_firm_idx on public.prediction_records (firm_id, created_at desc);
create index if not exists prediction_run_idx on public.prediction_records (run_id);

create table if not exists public.outcome_records (
  id                    uuid primary key default gen_random_uuid(),
  prediction_record_id  uuid not null references public.prediction_records (id) on delete cascade,
  actual_value          double precision not null,
  source                text,                       -- manual | csv | api
  recorded_at           timestamptz not null default now()
);
create index if not exists outcome_pred_idx on public.outcome_records (prediction_record_id);

-- RLS: reads scoped by firm ownership (writes via the service role).
alter table public.prediction_records enable row level security;
alter table public.outcome_records enable row level security;

create policy prediction_select on public.prediction_records for select using (
  auth.uid() = (select owner_id from public.firms where id = firm_id));

create policy outcome_select on public.outcome_records for select using (
  auth.uid() = (select owner_id from public.firms
                where id = (select firm_id from public.prediction_records
                            where id = prediction_record_id)));
