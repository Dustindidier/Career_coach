-- Run once in your Supabase project's SQL Editor.
create table if not exists public.career_workspace (
  id integer primary key check (id = 1),
  body jsonb not null
);
alter table public.career_workspace enable row level security;
revoke all on table public.career_workspace from anon, authenticated;
grant select, insert, update on table public.career_workspace to service_role;
-- No public policies. Only the server's service-role key can access records.

-- Non-destructive upgrade: existing bodies are preserved.
alter table public.career_workspace add column if not exists revision bigint not null default 0;
