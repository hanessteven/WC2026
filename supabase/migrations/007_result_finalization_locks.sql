-- ============================================================
-- 007_result_finalization_locks.sql
-- Add per-group and per-golden-boot result finalization locks.
-- Admins can lock results to prevent accidental edits after entering them.
-- Run this in the Supabase SQL editor.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- RESULTS GROUP LOCK
-- One row per group (A–L); admin can lock/unlock each group
-- individually to mark final results and prevent edits.
-- ────────────────────────────────────────────────────────────
create table if not exists results_group_lock (
  group_letter char(1) primary key,
  is_locked    boolean not null default false
);

-- Pre-seed all 12 groups, unlocked.
insert into results_group_lock (group_letter, is_locked)
values ('A', false), ('B', false), ('C', false), ('D', false),
       ('E', false), ('F', false), ('G', false), ('H', false),
       ('I', false), ('J', false), ('K', false), ('L', false)
on conflict (group_letter) do nothing;


-- ────────────────────────────────────────────────────────────
-- RESULTS GOLDEN BOOT LOCK
-- Single-row table (id = 1); admin can lock the golden boot
-- results once the top scorer is finalized.
-- ────────────────────────────────────────────────────────────
create table if not exists results_golden_boot_lock (
  id        int primary key default 1,
  is_locked boolean not null default false,
  check (id = 1)  -- enforce single row
);

-- Pre-seed the single row, unlocked.
insert into results_golden_boot_lock (id, is_locked)
values (1, false)
on conflict (id) do nothing;