-- ============================================================
-- 002_rls.sql  —  WC2026 Predictor: Row-Level Security
-- Run AFTER 001_schema.sql.
--
-- Strategy:
--   - Anon key  → regular users; RLS enforces per-user access.
--   - Service role key → admin writes; bypasses RLS entirely.
--   So admin-write policies are not needed here — the service
--   role client in the app handles all admin mutations.
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- PROFILES
-- Everyone can see all profiles (display names on leaderboard).
-- Users can only update their own row.
-- ────────────────────────────────────────────────────────────
alter table profiles enable row level security;

create policy "profiles: authenticated read all"
  on profiles for select
  to authenticated
  using (true);

create policy "profiles: own row insert"
  on profiles for insert
  to authenticated
  with check (auth.uid() = id);

create policy "profiles: own row update"
  on profiles for update
  to authenticated
  using (auth.uid() = id);


-- ────────────────────────────────────────────────────────────
-- ALLOWED EMAILS
-- Authenticated users can read (needed to check whitelist).
-- Writes are service-role only (RLS blocks anon writes).
-- ────────────────────────────────────────────────────────────
alter table allowed_emails enable row level security;

create policy "allowed_emails: authenticated read"
  on allowed_emails for select
  to authenticated
  using (true);


-- ────────────────────────────────────────────────────────────
-- SEED TABLES (read-only for all authenticated users)
-- ────────────────────────────────────────────────────────────
alter table seed_groups enable row level security;
create policy "seed_groups: authenticated read"
  on seed_groups for select to authenticated using (true);

alter table seed_teams enable row level security;
create policy "seed_teams: authenticated read"
  on seed_teams for select to authenticated using (true);

alter table seed_players enable row level security;
create policy "seed_players: authenticated read"
  on seed_players for select to authenticated using (true);

alter table bonus_question_defs enable row level security;
create policy "bonus_question_defs: authenticated read"
  on bonus_question_defs for select to authenticated using (true);


-- ────────────────────────────────────────────────────────────
-- LOCK STATE (read-only for all authenticated users)
-- ────────────────────────────────────────────────────────────
alter table lock_state enable row level security;

create policy "lock_state: authenticated read"
  on lock_state for select to authenticated using (true);


-- ────────────────────────────────────────────────────────────
-- REAL BRACKET (read-only for all authenticated users)
-- ────────────────────────────────────────────────────────────
alter table real_bracket enable row level security;

create policy "real_bracket: authenticated read"
  on real_bracket for select to authenticated using (true);


-- ────────────────────────────────────────────────────────────
-- TOURNAMENT RESULTS (read-only for all authenticated users)
-- ────────────────────────────────────────────────────────────
alter table results_group_stage enable row level security;
create policy "results_group_stage: authenticated read"
  on results_group_stage for select to authenticated using (true);

alter table results_player_goals enable row level security;
create policy "results_player_goals: authenticated read"
  on results_player_goals for select to authenticated using (true);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: GROUP STAGE
-- Users read/write only their own rows.
-- ────────────────────────────────────────────────────────────
alter table predictions_group_stage enable row level security;

create policy "pgs: own rows select"
  on predictions_group_stage for select
  to authenticated
  using (auth.uid() = user_id);

create policy "pgs: own rows insert"
  on predictions_group_stage for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "pgs: own rows update"
  on predictions_group_stage for update
  to authenticated
  using (auth.uid() = user_id);

create policy "pgs: own rows delete"
  on predictions_group_stage for delete
  to authenticated
  using (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: CHAMPION
-- ────────────────────────────────────────────────────────────
alter table predictions_champion enable row level security;

create policy "pc: own row select"
  on predictions_champion for select
  to authenticated
  using (auth.uid() = user_id);

create policy "pc: own row insert"
  on predictions_champion for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "pc: own row update"
  on predictions_champion for update
  to authenticated
  using (auth.uid() = user_id);

create policy "pc: own row delete"
  on predictions_champion for delete
  to authenticated
  using (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: KNOCKOUT BRACKET
-- ────────────────────────────────────────────────────────────
alter table predictions_bracket enable row level security;

create policy "pb: own rows select"
  on predictions_bracket for select
  to authenticated
  using (auth.uid() = user_id);

create policy "pb: own rows insert"
  on predictions_bracket for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "pb: own rows update"
  on predictions_bracket for update
  to authenticated
  using (auth.uid() = user_id);

create policy "pb: own rows delete"
  on predictions_bracket for delete
  to authenticated
  using (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: GOLDEN BOOT
-- ────────────────────────────────────────────────────────────
alter table predictions_golden_boot enable row level security;

create policy "pgb: own rows select"
  on predictions_golden_boot for select
  to authenticated
  using (auth.uid() = user_id);

create policy "pgb: own rows insert"
  on predictions_golden_boot for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "pgb: own rows delete"
  on predictions_golden_boot for delete
  to authenticated
  using (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: BONUS
-- ────────────────────────────────────────────────────────────
alter table predictions_bonus enable row level security;

create policy "pbonus: own rows select"
  on predictions_bonus for select
  to authenticated
  using (auth.uid() = user_id);

create policy "pbonus: own rows insert"
  on predictions_bonus for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "pbonus: own rows update"
  on predictions_bonus for update
  to authenticated
  using (auth.uid() = user_id);

create policy "pbonus: own rows delete"
  on predictions_bonus for delete
  to authenticated
  using (auth.uid() = user_id);


-- ────────────────────────────────────────────────────────────
-- SCORES (leaderboard — everyone reads, service role writes)
-- ────────────────────────────────────────────────────────────
alter table scores enable row level security;

create policy "scores: authenticated read"
  on scores for select to authenticated using (true);