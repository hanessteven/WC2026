# 12 — Scoring Engine

**Status:** 🔲 Not started
**Depends on:** 03, 06–11
**Module:** `src/scoring.py` — **pure Python, no `st.*` imports.**

## Goal
The heart of the app: take a user's predictions and the actual results and produce a scoring breakdown. Must work on **partial** tournament data and be **idempotent**.

## Requirements
- **Inputs:** `UserPredictions` + `TournamentResults`. **Output:** `ScoringBreakdown` (per-category points + total).
- **Categories:**
  - **Group stage:** correct qualifier, correct exact position, correct third-place advancer.
  - **Knockout:** exact per-match winner, weighted per round (R32=1, R16=2, QF=3, SF=5, Final=8).
  - **Champion pick:** large fixed reward if correct (+ dark-horse bonus).
  - **Golden boot:** points per goal by drafted players.
  - **Bonus:** 2 pts each; **tie-aware** — any of the admin-marked correct options counts.
- **Partial data:** only score categories/rounds for which results exist; absent results contribute 0, not errors.
- **Idempotency:** running scoring twice on the same inputs yields identical output.
- **Configurable point values:** read from a single source (constants/config) so weights can be tuned without code changes elsewhere.

## Acceptance criteria (tests required — see [../testing.md](../testing.md))
- Partial-data scenarios: group-only; group + R32; incremental round additions update totals correctly.
- Tie scenarios: bonus question with multiple correct options awards all matching users.
- Idempotency: repeated calculation is stable.
- Totals match `scoring_rules.md` for crafted fixtures.

## TODO
- Finalize champion / dark-horse / golden-boot scoring values (cross-ref features 07, 08).