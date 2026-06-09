-- 006_dark_horse_eligible.sql
-- Add dark_horse_eligible flag to seed_teams.
-- Default true so existing rows are unaffected until the seed loader re-runs.
alter table seed_teams
  add column if not exists is_dark_horse_eligible bool not null default true;