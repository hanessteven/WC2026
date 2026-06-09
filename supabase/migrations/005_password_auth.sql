-- ============================================================
-- 005_password_auth.sql
-- Switch from Supabase Auth (magic link) to self-contained
-- email + password auth. Profiles are no longer tied to
-- auth.users; we generate our own UUIDs and store a bcrypt hash.
-- Run this in the Supabase SQL editor.
-- ============================================================

-- 1. Detach profiles.id from auth.users so we can create rows ourselves.
alter table profiles drop constraint if exists profiles_id_fkey;

-- 2. Let profiles generate their own primary key.
alter table profiles alter column id set default gen_random_uuid();

-- 3. Store the bcrypt password hash (null = not yet registered).
alter table profiles add column if not exists password_hash text;

-- 4. Email must be unique — it's the login handle.
--    (If this errors on duplicates, clear stale test rows first:
--     delete from profiles where password_hash is null;)
alter table profiles add constraint profiles_email_unique unique (email);

-- 5. Retire the Supabase-Auth signup trigger; we create profiles in-app now.
drop trigger if exists on_auth_user_created on auth.users;
drop function if exists handle_new_user();