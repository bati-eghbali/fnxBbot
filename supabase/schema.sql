-- Phoenix Site Bot: conversation history and agent traces.
-- Applied automatically by backend/apply_schema.py (idempotent).

create table if not exists public.conversations (
    id          uuid primary key default gen_random_uuid(),
    title       text not null default '',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists public.messages (
    id               bigint generated always as identity primary key,
    conversation_id  uuid not null references public.conversations(id) on delete cascade,
    role             text not null check (role in ('user', 'assistant')),
    content          text not null,
    status           text,                          -- answered | not_found | refer | personal | advice | off_topic | greeting | error
    sources          jsonb not null default '[]'::jsonb,
    trace            jsonb not null default '[]'::jsonb,
    created_at       timestamptz not null default now()
);

create index if not exists messages_conversation_idx on public.messages (conversation_id, id);
create index if not exists conversations_updated_idx on public.conversations (updated_at desc);

-- RLS on with no policies: only the backend's secret/service key can read or write.
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- Newer projects do not grant table access by default. Only the backend role gets it;
-- anon / authenticated (browser keys) get nothing.
grant select, insert, update, delete on public.conversations, public.messages to service_role;
revoke all on public.conversations, public.messages from anon, authenticated;
