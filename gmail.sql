-- Server-only OAuth credentials, encrypted using Supabase Vault.
-- This never stores tokens in the exported career workspace.
create extension if not exists supabase_vault with schema vault;

create or replace function public.career_gmail_read()
returns jsonb language sql security definer set search_path = '' as $$
  select decrypted_secret::jsonb from vault.decrypted_secrets where name='nextchapter:gmail' limit 1;
$$;

create or replace function public.career_gmail_write(token_body jsonb)
returns void language plpgsql security definer set search_path = '' as $$
declare secret_id uuid;
begin
  perform pg_catalog.pg_advisory_xact_lock(72391847);
  select id into secret_id from vault.secrets where name='nextchapter:gmail' limit 1;
  if secret_id is null then
    perform vault.create_secret(token_body::text, 'nextchapter:gmail', 'Next Chapter Gmail OAuth');
  else
    perform vault.update_secret(secret_id, token_body::text);
  end if;
end;
$$;

create or replace function public.career_gmail_delete()
returns void language sql security definer set search_path = '' as $$
  delete from vault.secrets where name='nextchapter:gmail';
$$;
revoke all on function public.career_gmail_read() from public, anon, authenticated;
revoke all on function public.career_gmail_write(jsonb) from public, anon, authenticated;
revoke all on function public.career_gmail_delete() from public, anon, authenticated;
grant execute on function public.career_gmail_read() to service_role;
grant execute on function public.career_gmail_write(jsonb) to service_role;
grant execute on function public.career_gmail_delete() to service_role;
