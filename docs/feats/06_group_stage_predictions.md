# 06 — Group Stage Predictions

**Status:** 🔲 Not started
**Depends on:** 03, 04, 05

## Goal
Let each user rank the 4 teams in all 12 groups (1st–4th) and select the 8 best third-place teams that they predict will advance.

## Requirements
- For each group A–L, the user assigns a 1–4 ranking to its four teams.
- Across all groups, the user selects exactly **8 third-place advancers** (the 8-of-12 third-place qualification rule for the 48-team format).
- **Save & edit** freely until the `group_stage` lock is set (feature 10). Read-only once locked.
- **Validation:** every group fully ranked, no duplicate ranks; exactly 8 third-place picks.
- Persist via the user's own prediction rows (RLS-protected).

## Scoring impact (see [../scoring_rules.md](../scoring_rules.md))
- Correct qualifier (top 2): points per team.
- Correct exact position: bonus per team.
- Correct third-place advancer: points per team.

## Acceptance criteria
- Submit, reload, and edit preserve the user's picks.
- Validation blocks incomplete/invalid rankings and wrong third-place counts.
- Locking makes the page read-only.

## TODO
- Choose ranking UI pattern (drag-and-drop vs four selectboxes per group).
- Decide how third-place selection is surfaced (checkbox list of the 12 third-placed teams *as the user predicts them*).