# Architecture & Database Schema

## Tech Stack
- **Frontend:** Streamlit (thin UI layer)
- **DB:** Supabase (PostgreSQL)
- **Auth:** Supabase magic link, restricted to an email whitelist
- **Deployment:** Streamlit Community Cloud

## Finalized Architectural Decisions
- **Authentication:** Supabase magic-link sign-in, allowed only for whitelisted emails. Admin status is derived from an `ADMIN_EMAILS` config list.
- **Prediction locking:** Admin-controlled **manual locks**, at **per-category + per-round** granularity (`group_stage`, `champion`, `golden_boot`, `bonus`, and each knockout round). No automatic deadlines.
- **Results entry:** A dedicated **admin page inside the app** (no direct DB editing required).
- **Bracket model:** **Wave-based** — users lock group picks at group-stage kickoff; the admin enters the *actual* matchups for each knockout round, which populate the bracket everyone picks from. A separate **upfront champion pick** locks at tournament start. This avoids per-user self-seeding and makes knockout scoring exact.
- **Static data:** Seeded from versioned files in the repo (`seed/`), loaded via an idempotent script.

## Module Layout
- `src/app.py` — Streamlit entrypoint (thin).
- `src/config.py` — env/secrets + whitelist loading.
- `src/db.py` — cached Supabase client; **all DB queries live here.**
- `src/auth.py` — magic-link + whitelist auth.
- `src/models.py` — Pydantic models (no `st.*`).
- `src/scoring.py` — pure scoring engine (no `st.*`).
- `src/pages/` — per-feature Streamlit pages.

## Schema (high level)
Detailed column definitions are tracked in [database_schema.md](database_schema.md) (TODO). Tables include: `profiles`, `allowed_emails`, seed tables (`seed_teams`, `seed_groups`, `seed_players`, `bonus_question_defs`), prediction tables (`predictions_group_stage`, `predictions_champion`, `predictions_bracket`, `predictions_golden_boot`, `predictions_bonus`), `real_bracket`, `tournament_results`, `lock_state`, and `scores`.

## Connectivity & Security
- Use `supabase-py` for all interactions; centralize queries in `src/db.py`.
- **RLS:** users read/write only their own predictions; everyone reads seed/results/locks/scores; only admins write results, locks, real bracket, and seed data.

## Feature Roadmap
See [feats/README.md](feats/README.md) for the numbered, dependency-ordered feature specs.