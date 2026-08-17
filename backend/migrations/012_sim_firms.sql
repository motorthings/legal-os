-- Phase 1 — firm CRUD + intake → config. Operator-only: ownership through auth.users,
-- RLS scoped by auth.uid(). (Back on Supabase after the Fly detour.)
-- Convention: snake_case plural tables, UUID PKs, created_at/updated_at, RLS per operation.

-- ---------------------------------------------------------------------------
-- firms — the operator's portfolio. status: draft | ready | running | complete
-- ---------------------------------------------------------------------------
create table public.firms (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  owner_id    uuid not null references auth.users (id),
  status      text not null default 'draft',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index firms_owner_idx on public.firms (owner_id);

-- ---------------------------------------------------------------------------
-- firm_configs — versioned JSONB. Each row is the EXACT full-config contract object
-- (the one run_config.build_sim_config + build_objective consume). One active per firm.
-- ---------------------------------------------------------------------------
create table public.firm_configs (
  id          uuid primary key default gen_random_uuid(),
  firm_id     uuid not null references public.firms (id) on delete cascade,
  version     int  not null default 1,
  config      jsonb not null,
  is_active   boolean not null default false,
  created_at  timestamptz not null default now()
);
create unique index firm_configs_active_one on public.firm_configs (firm_id) where is_active;
create index firm_configs_firm_idx on public.firm_configs (firm_id, version desc);

-- ---------------------------------------------------------------------------
-- calibrations — coefficient calibration from firm experience (Phase 3)
-- ---------------------------------------------------------------------------
create table public.calibrations (
  id                    uuid primary key default gen_random_uuid(),
  firm_id               uuid not null references public.firms (id) on delete cascade,
  coefficient_id        text not null,
  value                 double precision not null,
  source                text,
  calibration_question  text,
  created_at            timestamptz not null default now(),
  unique (firm_id, coefficient_id)
);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger firms_set_updated_at before update on public.firms
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security — one policy per operation, scoped by auth.uid()
-- ---------------------------------------------------------------------------
alter table public.firms         enable row level security;
alter table public.firm_configs  enable row level security;
alter table public.calibrations  enable row level security;

create policy firms_select on public.firms
  for select using (auth.uid() = owner_id);
create policy firms_insert on public.firms
  for insert with check (auth.uid() = owner_id);
create policy firms_update on public.firms
  for update using (auth.uid() = owner_id);
create policy firms_delete on public.firms
  for delete using (auth.uid() = owner_id);

create policy fc_select on public.firm_configs for select using (
  auth.uid() = (select owner_id from public.firms where id = firm_id));
create policy fc_insert on public.firm_configs for insert with check (
  auth.uid() = (select owner_id from public.firms where id = firm_id));
create policy fc_update on public.firm_configs for update using (
  auth.uid() = (select owner_id from public.firms where id = firm_id));

create policy cal_select on public.calibrations for select using (
  auth.uid() = (select owner_id from public.firms where id = firm_id));
create policy cal_insert on public.calibrations for insert with check (
  auth.uid() = (select owner_id from public.firms where id = firm_id));
