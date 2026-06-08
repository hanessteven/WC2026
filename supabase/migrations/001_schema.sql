-- ============================================================
-- 001_schema.sql  —  WC2026 Predictor: all tables + indexes
-- Run this in the Supabase SQL editor (Project > SQL Editor).
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- PROFILES
-- Auto-created on first sign-in via the trigger below.
-- ────────────────────────────────────────────────────────────
create table if not exists profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  email         text not null,
  display_name  text,
  created_at    timestamptz not null default now()
);

-- Auto-create a profile row whenever a user signs up.
create or replace function handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure handle_new_user();


-- ────────────────────────────────────────────────────────────
-- AUTH WHITELIST
-- ────────────────────────────────────────────────────────────
create table if not exists allowed_emails (
  email  text primary key
);


-- ────────────────────────────────────────────────────────────
-- SEED: GROUPS & TEAMS
-- ────────────────────────────────────────────────────────────
create table if not exists seed_groups (
  letter  char(1) primary key  -- 'A' through 'L'
);

create table if not exists seed_teams (
  id            serial primary key,
  name          text   not null unique,
  group_letter  char(1) not null references seed_groups(letter),
  flag_emoji    text
);

create index if not exists idx_seed_teams_group on seed_teams(group_letter);


-- ────────────────────────────────────────────────────────────
-- SEED: GOLDEN BOOT PLAYERS
-- ────────────────────────────────────────────────────────────
create table if not exists seed_players (
  id        serial primary key,
  name      text not null,
  team_name text references seed_teams(name),
  tier      int  not null,   -- 1 = top tier (most expensive)
  cost      int  not null    -- virtual dollars (e.g. 30, 15, 5)
);


-- ────────────────────────────────────────────────────────────
-- SEED: BONUS QUESTION DEFINITIONS
-- correct_options is null until the admin records results;
-- stored as a JSONB array to support ties (multiple correct).
-- ────────────────────────────────────────────────────────────
create table if not exists bonus_question_defs (
  id               serial primary key,
  question_text    text  not null,
  valid_options    jsonb not null,   -- e.g. ["USA","Mexico","Canada","Tie"]
  correct_options  jsonb,            -- null until results; e.g. ["USA","Mexico"]
  point_value      int   not null default 2
);


-- ────────────────────────────────────────────────────────────
-- LOCK STATE
-- One row per lockable category, pre-seeded below.
-- ────────────────────────────────────────────────────────────
create table if not exists lock_state (
  category   text primary key,  -- see seed insert below
  is_locked  bool not null default false,
  locked_at  timestamptz,
  locked_by  text                -- admin email
);

-- Pre-seed all lock categories (idempotent).
insert into lock_state (category) values
  ('group_stage'),
  ('champion'),
  ('golden_boot'),
  ('bonus'),
  ('R32'),
  ('R16'),
  ('QF'),
  ('SF'),
  ('F')
on conflict (category) do nothing;


-- ────────────────────────────────────────────────────────────
-- REAL BRACKET
-- Admin populates each round's matchups as the tournament
-- progresses. winner / is_penalty filled in after each match.
-- ────────────────────────────────────────────────────────────
create table if not exists real_bracket (
  id          serial primary key,
  round       text not null,    -- 'R32','R16','QF','SF','F'
  slot        int  not null,    -- 1-based slot within the round
  team_a      text not null,
  team_b      text not null,
  winner      text,             -- null until result entered
  is_penalty  bool not null default false,
  unique (round, slot)
);


-- ────────────────────────────────────────────────────────────
-- TOURNAMENT RESULTS: GROUP STAGE
-- Admin enters final group standings after groups conclude.
-- final_ranking: JSONB array of 4 team names [1st, 2nd, 3rd, 4th].
-- third_place_advances: true if this group's 3rd-place team is
-- one of the 8 advancing third-placers.
-- ────────────────────────────────────────────────────────────
create table if not exists results_group_stage (
  group_letter        char(1) primary key references seed_groups(letter),
  final_ranking       jsonb not null,         -- [team1, team2, team3, team4]
  third_place_advances bool not null default false,
  updated_at          timestamptz not null default now()
);


-- ────────────────────────────────────────────────────────────
-- TOURNAMENT RESULTS: PLAYER GOALS (Golden Boot)
-- ────────────────────────────────────────────────────────────
create table if not exists results_player_goals (
  player_id     int primary key references seed_players(id),
  goals_scored  int not null default 0,
  updated_at    timestamptz not null default now()
);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: GROUP STAGE
-- One row per (user, group). predicted_ranking is a JSONB
-- array of 4 team names [1st, 2nd, 3rd, 4th].
-- third_place_advances: user predicts this group's 3rd-place
-- team will be one of the 8 advancing; exactly 8 of 12 must
-- be true (enforced in app logic).
-- ────────────────────────────────────────────────────────────
create table if not exists predictions_group_stage (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references profiles(id) on delete cascade,
  group_letter         char(1) not null references seed_groups(letter),
  predicted_ranking    jsonb not null,
  third_place_advances bool not null default false,
  updated_at           timestamptz not null default now(),
  unique (user_id, group_letter)
);

create index if not exists idx_pgs_user on predictions_group_stage(user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: CHAMPION (upfront, locked at tournament start)
-- ────────────────────────────────────────────────────────────
create table if not exists predictions_champion (
  user_id     uuid primary key references profiles(id) on delete cascade,
  champion    text not null,
  dark_horse  text,           -- optional
  updated_at  timestamptz not null default now()
);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: KNOCKOUT BRACKET
-- One row per (user, real_bracket matchup).
-- ────────────────────────────────────────────────────────────
create table if not exists predictions_bracket (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references profiles(id) on delete cascade,
  matchup_id        int  not null references real_bracket(id),
  predicted_winner  text not null,
  updated_at        timestamptz not null default now(),
  unique (user_id, matchup_id)
);

create index if not exists idx_pb_user     on predictions_bracket(user_id);
create index if not exists idx_pb_matchup  on predictions_bracket(matchup_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: GOLDEN BOOT DRAFT
-- Join table — user drafts multiple players from seed_players.
-- Budget enforcement (≤ $100) is in app logic.
-- ────────────────────────────────────────────────────────────
create table if not exists predictions_golden_boot (
  user_id    uuid not null references profiles(id) on delete cascade,
  player_id  int  not null references seed_players(id),
  primary key (user_id, player_id)
);

create index if not exists idx_pgb_user on predictions_golden_boot(user_id);


-- ────────────────────────────────────────────────────────────
-- PREDICTIONS: BONUS QUESTIONS
-- One row per (user, question).
-- ────────────────────────────────────────────────────────────
create table if not exists predictions_bonus (
  user_id         uuid not null references profiles(id) on delete cascade,
  question_id     int  not null references bonus_question_defs(id),
  chosen_option   text not null,
  updated_at      timestamptz not null default now(),
  primary key (user_id, question_id)
);

create index if not exists idx_pbonus_user on predictions_bonus(user_id);


-- ────────────────────────────────────────────────────────────
-- SCORES (cached scoring breakdown per user)
-- Written only by the scoring engine via the service-role key.
-- ────────────────────────────────────────────────────────────
create table if not exists scores (
  user_id           uuid primary key references profiles(id) on delete cascade,
  group_stage_pts   int not null default 0,
  bracket_pts       int not null default 0,
  champion_pts      int not null default 0,
  golden_boot_pts   int not null default 0,
  bonus_pts         int not null default 0,
  total_pts         int not null default 0,
  calculated_at     timestamptz not null default now()
);

create index if not exists idx_scores_total on scores(total_pts desc);