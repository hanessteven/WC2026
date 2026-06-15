-- ============================================================
-- 009_unlisted_golden_boot_winner.sql
-- Store information about an unlisted player who won the Golden Boot
-- (not in the seed_players list).
-- Run this in the Supabase SQL editor.
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- RESULTS UNLISTED GOLDEN BOOT WINNER
-- Records a top scorer who is not in the seeded players list.
-- For documentation only; no one gets points since they weren't
-- available for drafting (seeded list was locked).
-- ────────────────────────────────────────────────────────────
create table if not exists results_unlisted_golden_boot_winner (
  id              serial primary key,
  player_name     text not null,
  goals_scored    int not null,
  created_at      timestamptz default now()
);