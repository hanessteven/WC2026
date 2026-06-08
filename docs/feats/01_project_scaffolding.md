# 01 — Project Scaffolding & Configuration

**Status:** 🔲 Not started
**Depends on:** —

## Goal
Stand up the repository skeleton, dependency management, configuration/secrets loading, and a cached Supabase client so every later feature has a stable foundation.

## Requirements
- **Directory structure:**
  ```
  src/
    app.py            # Streamlit entrypoint (thin)
    config.py         # env/secrets loading
    db.py             # Supabase client (cached singleton)
    auth.py           # (stub for feature 05)
    models.py         # (stub for feature 03)
    scoring.py        # (stub for feature 12)
    pages/            # Streamlit multipage UIs
  seed/               # seed data files (feature 04)
  tests/              # pytest suite
  supabase/migrations/ # SQL migrations (feature 02)
  ```
- **`requirements.txt`:** `streamlit`, `supabase`, `pydantic`, `python-dotenv`, `pytest`. TODO: pin versions; add any extras (e.g. `pandas`) only if actually used.
- **`.gitignore`:** must include `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`, `.DS_Store`, `.streamlit/secrets.toml`.
- **`config.py`:** loads `SUPABASE_URL`, `SUPABASE_KEY`, and `ADMIN_EMAILS` (comma-separated whitelist of admins) from environment / `st.secrets`. Fails fast with a clear message if missing.
- **`db.py`:** returns a Supabase client wrapped in `st.cache_resource` so the connection is reused across reruns.
- **`.env.example`:** template documenting every required variable (no real secrets committed).

## Acceptance criteria
- `streamlit run src/app.py` boots and renders a placeholder page.
- The app reads config from secrets and successfully constructs a Supabase client (a trivial query / health check succeeds).
- `pytest` runs (even with zero/placeholder tests) without import errors.

## TODO
- Finalize dependency versions.
- Decide multipage layout convention (Streamlit `pages/` vs manual router).