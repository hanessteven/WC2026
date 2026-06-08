# 03 — Data Models (Pydantic)

**Status:** ✅ Done
**Depends on:** 02

## Goal
Implement `src/models.py` with Pydantic models for every data shape. Detailed field lists live in [../models.md](../models.md). **No `st.*` imports** in this module.

## Requirements
- Implement the models described in `models.md`, adapted for the **wave-based** design:
  - `UserProfile`
  - `GroupStagePrediction` (group letter + ranked 4 teams)
  - `ThirdPlaceSelection` (the 8 advancing third-place teams)
  - `ChampionPick` (champion + optional dark horse)
  - `RealMatchup` (admin-entered actual matchup: round, slot, team_a, team_b)
  - `RoundPick` (user's predicted winner for a given real matchup)
  - `GoldenBootSelection` (player + cost)
  - `BonusAnswer` (question_id + chosen option)
  - `UserPredictions` (aggregate of the above)
  - `TournamentResults` (group standings, match winners, penalties, goals, bonus answers — supports **multiple correct answers** per bonus question for ties)
  - `LockState` (per-category + per-round flags)
  - `ScoringBreakdown` (per-category points + total)
- **Validators:**
  - Group ranking must contain exactly the 4 teams of that group, no duplicates.
  - Exactly 8 third-place selections.
  - Golden boot total cost ≤ \$100 (budget configurable).
  - Bonus answer must be one of the question's valid options.

## Acceptance criteria
- Valid payloads parse; invalid ones raise clear `ValidationError`s.
- Budget, uniqueness, and option-membership validators are unit-tested.

## TODO
- Confirm exact field names align with the final DB schema (feature 02).