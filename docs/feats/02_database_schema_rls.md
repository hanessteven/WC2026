# 02 — Database Schema & RLS Policies

**Status:** ✅ Done
**Depends on:** 01

## Goal
Create the Supabase (PostgreSQL) tables and Row-Level Security policies that back every feature. Detailed column-level definitions live in [../database_schema.md](../database_schema.md) (still `TODO` there).

## Tables (high level)
- **profiles** — user identity (links to Supabase `auth.users`); `display_name`.
- **allowed_emails** — the auth whitelist (feature 05).
- **seed_teams / seed_groups** — the 48 teams and 12 groups (feature 04).
- **seed_players** — golden boot candidates with tier cost (feature 04).
- **bonus_question_defs** — question text, valid options (JSONB), point value (feature 04).
- **predictions_group_stage** — per user: group rankings + 8 third-place advancers.
- **predictions_champion** — per user: upfront champion (+ optional dark horse).
- **predictions_bracket** — per user, per round, per real-matchup: predicted winner.
- **predictions_golden_boot** — per user: drafted players.
- **predictions_bonus** — per user: chosen option per question.
- **real_bracket** — admin-entered actual matchups per knockout round (drives the wave bracket).
- **tournament_results** — admin-entered results (group standings, match winners, penalties, goals, bonus answers).
- **lock_state** — per-category and per-round lock flags (feature 10).
- **scores** — cached per-user scoring breakdown (feature 12/13).

## RLS requirements
- Users may **read/write only their own** prediction rows.
- All authenticated users may **read** seed data, results, real_bracket, lock_state, and leaderboard/scores.
- Only **admins** (email in `ADMIN_EMAILS`) may write `tournament_results`, `real_bracket`, `lock_state`, and seed tables.
- Writes to prediction tables are rejected when the relevant `lock_state` flag is set (enforce in app logic; TODO: consider a DB trigger for defense-in-depth).

## Migration approach
- SQL migration files under `supabase/migrations/`.
- TODO: choose migration tooling (Supabase CLI vs hand-run SQL).

## Acceptance criteria
- All tables exist with FKs.
- User A cannot read or modify User B's predictions (RLS verified).
- A non-admin cannot write results/locks; an admin can.

## TODO
- Fill detailed columns/types/constraints in `database_schema.md`.
- Decide whether lock enforcement is app-only or also DB-trigger backed.