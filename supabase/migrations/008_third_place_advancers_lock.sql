-- ============================================================
-- 008_third_place_advancers_lock.sql
-- Add a lock for 3rd place advancers selection.
-- Admins can lock this once 8 teams are chosen.
-- Run this in the Supabase SQL editor.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- RESULTS THIRD PLACE ADVANCERS LOCK
-- Single-row table (id = 1); admin can lock/unlock to finalize
-- which 8 third-place teams advance to the knockout round.
-- ────────────────────────────────────────────────────────────
create table if not exists results_third_place_advancers_lock (
  id        int primary key default 1,
  is_locked boolean not null default false,
  check (id = 1)  -- enforce single row
);

-- Pre-seed the single row, unlocked.
insert into results_third_place_advancers_lock (id, is_locked)
values (1, false)
on conflict (id) do nothing;