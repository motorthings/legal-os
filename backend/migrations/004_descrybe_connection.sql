-- ============================================================================
-- Legal AI OS — Descrybe Connection (OAuth)
-- ============================================================================
-- Stores each user's Descrybe OAuth tokens so the app can call the Descrybe
-- Legal Engine on their behalf. Tokens are encrypted at rest by the backend
-- (Fernet) and are only ever read via the service role — never exposed to the
-- browser. RLS is enabled with no per-user policies, so only the backend's
-- service-role client can read or write these rows.
-- ============================================================================

create table if not exists descrybe_connections (
    id                  uuid primary key default uuid_generate_v4(),
    user_id             uuid not null references user_profiles(id) on delete cascade,

    -- OAuth client identity (needed to refresh the token)
    oauth_client_id     text not null,
    oauth_client_secret text,                          -- nullable: public client uses "none" auth
    token_endpoint      text not null,

    -- Encrypted token material (Fernet, base64) — never plaintext
    access_token        text,
    refresh_token       text,
    token_type          text not null default 'Bearer',
    scopes              text,                          -- space-delimited
    expires_at          numeric,                       -- unix epoch seconds

    -- Connection metadata
    status              text not null default 'active',   -- active | revoked | error
    last_refresh_at     timestamptz,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),

    constraint descrybe_connections_user_unique unique (user_id)
);

create index idx_descrybe_connections_user on descrybe_connections(user_id);

-- Row-level security: enable but add no policies. The service-role client
-- (backend) bypasses RLS; anonymous/authenticated clients are denied. This
-- keeps token material server-side only.
alter table descrybe_connections enable row level security;
