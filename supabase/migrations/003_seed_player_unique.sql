-- 003_seed_player_unique.sql
-- Adds unique constraint on seed_players.name so the loader can upsert idempotently.
alter table seed_players add constraint seed_players_name_unique unique (name);