# Project: World Cup 2026 Prediction App

## Overview
A web-based prediction application for the 2026 World Cup, built with Streamlit and backed by Supabase (PostgreSQL). Users predict outcomes to compete for points.

## Documentation Index
- [Architecture & Schema](docs/architecture.md)
- [Scoring Rules](docs/scoring_rules.md)
- [Bonus Questions & Logic](docs/bonus_questions.md)
- [Data Models](docs/models.md)
- [Database Schema (Detailed)](docs/database_schema.md)
- [Local Development Setup](docs/local_setup.md)
- [Testing Strategy](docs/testing.md)
- [Deployment & Release](docs/deployment.md)
- [Error Handling & Edge Cases](docs/error_handling.md)
- [Development Workflow](docs/development_workflow.md)
- [Feature Roadmap & Specs](docs/feats/README.md)

## Key Decisions (build to these)
- **Auth:** Supabase magic link, email-whitelisted; admins via `ADMIN_EMAILS`.
- **Locking:** admin manual locks, per-category + per-round.
- **Results entry:** admin page in the app.
- **Bracket:** wave-based (pick each round from the real matchups the admin enters) + an upfront champion pick locked at tournament start.
- **Knockout scoring:** exact per-match winner, Fibonacci per round.
- **Static data:** seed files in repo, loaded idempotently.
- **Build order:** follow the numbered specs in `docs/feats/`.

## Coding Standards
- **Framework:** Streamlit (keep UI thin).
- **Backend:** Supabase (PostgreSQL).
- **Logic:** Pure Python (module `src/scoring.py`). Use Pydantic for data validation.
- **Rules:**
  - **Type Safety:** Always use type hints.
  - **Efficiency:** Use `st.cache_data` for DB reads.
  - **Separation:** No `st.*` calls in `src/scoring.py` or `src/models.py`.
  - **Token Management:** Refer to specific files for instructions. Do not read `node_modules`, `.venv`, `__pycache__`, or `.git`.