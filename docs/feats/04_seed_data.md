# 04 — Seed Data

**Status:** 🔲 Not started
**Depends on:** 02, 03

## Goal
Populate the static reference data: the 48 teams in 12 groups, the golden boot candidate list with tier costs, the bonus question definitions, and the initial email whitelist.

## Requirements
- **Teams & groups:** official 2026 draw, Groups A–L (4 teams each). Stored as a versioned seed file (YAML/JSON) under `seed/`.
- **Golden boot players:** curated, tiered list with costs (e.g. Mbappé \$30, Pulisic \$10, sleepers \$5). Stored in `seed/`.
- **Bonus questions:** the questions from [../bonus_questions.md](../bonus_questions.md), each with `valid_options` and `point_value`.
- **Email whitelist:** initial allowed emails (admins flagged separately via `ADMIN_EMAILS` config).
- **Loader:** an idempotent script (`seed/load_seed.py` or similar) that upserts seed files into the DB and validates them against the feature-03 models before insert.

## Acceptance criteria
- Running the loader populates all seed tables; running it twice produces no duplicates/changes (idempotent).
- All seed rows validate against the Pydantic models.

## TODO
- Confirm the final golden boot player list + costs (cross-ref feature 08).
- Handle 2026 draw slots that are still playoff-pending placeholders (intercontinental / UEFA path winners) — decide on placeholder naming.
- Confirm bonus question set and point values.