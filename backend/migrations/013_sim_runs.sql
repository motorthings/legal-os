-- Phase 2 — the runner. `runs` tracks a Monte Carlo execution (progress + resume +
-- budget); `run_events` persists every progress/status event (SSE replay + crash-resume).
-- Written by the runner service via the service role (bypasses RLS); scoped for reads.

create table public.runs (
  id              uuid primary key default gen_random_uuid(),
  firm_id         uuid references public.firms (id) on delete set null,
  status          text not null default 'queued',   -- queued|running|complete|budget_exhausted|error
  provider        text not null default 'mock',
  total_seeds     int  not null default 20,
  seeds_completed int  not null default 0,
  budget          double precision,                 -- per-run USD cap
  max_cost        double precision,
  spend           double precision not null default 0.0,
  config_snapshot jsonb not null,
  report_ref      text,
  error           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index runs_firm_idx on public.runs (firm_id);
create index runs_status_idx on public.runs (status);

create table public.run_events (
  id         bigserial primary key,
  run_id     uuid not null references public.runs (id) on delete cascade,
  seq        bigint not null,
  ts         timestamptz not null default now(),
  kind       text not null,                        -- status|sprint|seed|report_ready|error
  payload    jsonb not null
);
create index run_events_run_seq_idx on public.run_events (run_id, seq);

create trigger runs_set_updated_at before update on public.runs
  for each row execute function public.set_updated_at();

-- RLS: reads scoped by firm ownership (the runner writes via the service role).
alter table public.runs       enable row level security;
alter table public.run_events enable row level security;

create policy runs_select on public.runs for select using (
  auth.uid() = (select owner_id from public.firms where id = firm_id));

create policy run_events_select on public.run_events for select using (
  auth.uid() = (select owner_id from public.firms where id = (select firm_id from public.runs where id = run_id)));
