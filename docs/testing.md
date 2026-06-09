# Testing Strategy

Automated tests cover the entire **non-UI** surface of the app. Streamlit page rendering
(`src/pages/**`, `src/app.py`, `src/components.py`, and the cookie/session flow in `src/auth.py` —
`restore_session`, `show_login_ui`) is verified manually / in a browser, not here.

See [feats/14_test_suite.md](feats/14_test_suite.md) for the feature spec and
[feats/15_bugs.md](feats/15_bugs.md) for issues the suite surfaced.

## Framework & layout
- **pytest** (`requirements.txt`). Config in `pytest.ini` (`testpaths = tests`).
- Tests live in `tests/`. Shared fixtures + the fake DB live in `tests/conftest.py`.

| File | Layer | Module under test |
|---|---|---|
| `tests/test_scoring.py` | unit | `src/scoring.py` — all 5 scorers + `calculate_scores` |
| `tests/test_models.py` | unit | `src/models.py` — core validators |
| `tests/test_models_extra.py` | unit | `src/models.py` — enum, defaults, construction edges |
| `tests/test_predictions_db.py` | unit + integ | `src/predictions.py` — leaderboard ranking, reads, save→cache-clear |
| `tests/test_score_runner.py` | integ | `src/score_runner.py` — full recalc flow |
| `tests/test_admin_db.py` | integ | `src/admin.py` — locks, result saves, reset |
| `tests/test_auth.py` | integ | `src/auth.py` — register / login / whitelist / admin |

## The fake Supabase client
Integration tests run against `tests/conftest.py::FakeSupabase`, an in-memory stand-in that mimics
the query-builder chain the app uses:
`table().select().eq().neq().in_().order().execute()` plus `insert`, `upsert(on_conflict=...)`,
`update`, and `delete`. Tables are lists of dicts; `.execute()` returns an object with `.data`.

It's injected via the `fake_db` fixture, which monkeypatches `src.db.get_admin_client`. Every
module imports that client lazily *inside* its functions, so the patch always takes effect — no
network, no real database.

**Known limitation:** the fake does not model PostgreSQL column defaults. A row inserted without an
optional column (e.g. `real_bracket.winner`) simply lacks that key rather than holding `NULL`, so
tests use `.get("winner")` rather than `["winner"]` for defaulted columns.

**Cache hygiene:** an autouse fixture calls `st.cache_data.clear()` around every test so
`@st.cache_data` reads never leak between cases.

## Scoring engine (`src/scoring.py`)
Tested thoroughly and independently of Streamlit, per the feature 12 acceptance criteria:
- **Per-category scorers:** group (qualifier + exact position + 3rd-place advancer), bracket
  (Fibonacci per-round weights), champion + dark horse, golden boot (incl. ties), bonus.
- **Partial data:** group-only; group + R32; later rounds contribute 0 until results exist.
- **Incremental updates:** adding a round's winner raises the total on the next recompute.
- **Ties:** bonus questions with multiple correct options award every matching user; joint
  top-scorers all satisfy the golden-boot check.
- **Idempotency:** recomputing on identical inputs yields identical output.

## Integration coverage
- **`recalculate_all_scores`:** a complete crafted tournament where one user predicts everything
  correctly asserts the exact per-category breakdown and total; a user with no predictions scores
  zero; every profile gets a `scores` row; repeated runs upsert (no duplicates) and are stable.
- **Admin saves:** group/match/goal/bonus saves persist *and* trigger a recalc; bonus ties award
  all matching users; `reset_user_picks` wipes all five prediction tables for one user only.
- **Auth:** bcrypt round-trips for real (register hashes, login verifies); whitelist gating and
  email normalization; legacy-row claim vs duplicate rejection; `is_admin` against `ADMIN_EMAILS`.

## Test data
Fixtures and small factory helpers live alongside the tests:
- `tests/conftest.py` — `FakeSupabase` + the `fake_db` / cache-clearing fixtures.
- `tests/test_score_runner.py::_seed_full_tournament` — a complete, internally-consistent
  tournament used as the integration baseline.
- Per-file helpers (`_raw`, `_make_players`, `_make_group_predictions`, etc.) build predictions and
  results for focused cases.

## Bug-tracking convention
A test that intentionally demonstrates a known, unfixed bug is marked
`@pytest.mark.xfail(strict=True)` and references a numbered entry in
[feats/15_bugs.md](feats/15_bugs.md). `strict=True` means the suite **fails if the bug ever
silently gets fixed** — at which point you remove the marker so the test becomes a normal guard.
Currently one such test tracks **BUG-1** (over-broad exception handling zeroes a whole user's
score).

## Running tests
```bash
pytest                              # whole suite
pytest -q                           # quiet
pytest tests/test_score_runner.py -v
pytest -rx                          # show reasons for xfailed tests
pytest --runxfail                   # force xfail tests to run as normal (to inspect a tracked bug)
pytest -k leaderboard               # filter by name
```
Coverage reporting is not currently configured; add `pytest-cov` and run `pytest --cov=src` if it's
wanted later.