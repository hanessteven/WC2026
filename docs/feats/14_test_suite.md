# 14 — Test Suite (Unit + Integration, non-UI)

**Status:** ✅ Done
**Depends on:** 03, 06–13
**Scope:** every non-UI module. Streamlit page rendering (`src/pages/**`, `src/app.py`,
`src/components.py`, the `show_login_ui`/`restore_session` cookie/session flow) is **out of
scope** — those are verified manually / with a browser, per [../testing.md](../testing.md).

## Goal
Lock down the whole testable surface of the app with automated tests so regressions surface
immediately, and flush out latent bugs in the modules that were never exercised without a
live database. Two layers:

- **Unit tests** — pure functions, no I/O: `src/scoring.py`, `src/models.py` validators,
  and the extracted leaderboard ranking helper.
- **Integration tests** — module orchestration against an **in-memory fake Supabase client**
  (no network, no real DB): `src/score_runner.py`, `src/predictions.py` read/write helpers,
  `src/admin.py`, and `src/auth.py` register/login.

## Approach
- **Fake Supabase** (`tests/conftest.py::FakeSupabase`) mimics the query-builder chain used by
  the app: `table().select().eq().neq().in_().order().execute()` plus
  `insert/upsert(on_conflict)/update/delete`. Tables are lists of dicts; `.execute()` returns an
  object with `.data`. Injected by monkeypatching `src.db.get_admin_client` (every module imports
  it lazily inside the function, so the patch always takes effect).
- **Cache hygiene:** an autouse fixture calls `st.cache_data.clear()` between tests so
  `@st.cache_data` reads never leak across cases.
- **Tests assert the spec, not the code.** Where current behavior diverges from
  `scoring_rules.md` / the feature specs, the test is written against the spec and the failure is
  logged in [15_bugs.md](15_bugs.md) to be fixed separately.

## Coverage map
| Module | Layer | What's covered |
|---|---|---|
| `src/scoring.py` | unit | all 5 category scorers + `calculate_scores`; partial-data, ties, idempotency (feat 12 AC) |
| `src/models.py` | unit | every validator: group ranking, third-place count, golden-boot budget, bonus option, breakdown total |
| `src/predictions.py` | unit + integ | `_assemble_leaderboard` ranking/ties; read transforms; save→cache-clear |
| `src/score_runner.py` | integ | full recalc flow predictions+results→scores; partial data; per-user isolation |
| `src/admin.py` | integ | lock toggle, group/match/goal/bonus saves trigger recalc, reset wipes all tables |
| `src/auth.py` | integ | register (new/legacy-claim/duplicate/not-whitelisted), login (ok/bad/unknown), whitelist normalization, `is_admin` |

## Acceptance criteria
- `pytest` runs green for every test that asserts **correct** (spec-compliant) behavior.
- Tests that intentionally expose a bug are marked `xfail(strict=True)` and reference a
  numbered entry in [15_bugs.md](15_bugs.md), so the suite stays green while the bug is tracked.
- No test touches the network or a real Supabase instance.

## Running
```
pytest                 # whole suite
pytest tests/test_score_runner.py -v
pytest -m "" -q        # include xfail summary
```