# 10 — Admin Panel (Results, Locks, Bracket Progression)

**Status:** 🔲 Not started
**Depends on:** 02, 03, 05 (admin auth)

## Goal
An admin-only page where you drive the tournament: toggle locks, enter results nightly, populate each knockout round's real matchups, and trigger score recalculation.

## Requirements (admin-only; gated by `is_admin`)
- **Lock controls:** per-category + per-round toggles — `group_stage`, `champion`, `golden_boot`, `bonus`, and each knockout round (`R32`, `R16`, `QF`, `SF`, `Final`). Flipping a lock makes that surface read-only for users.
- **Group results:** enter final standings per group + which 8 third-place teams advanced.
- **Bracket progression (drives the wave bracket, feature 11):**
  - After the group stage, enter the **real Round of 32 matchups** → this populates the R32 bracket users pick from.
  - After each round's results, enter the **next round's real matchups**.
- **Match results:** per knockout match, record winner (+ penalty-decided flag).
- **Golden boot goals:** record goals scored per player.
- **Bonus answers:** record the correct option(s) per question — supporting **multiple correct** for ties.
- **Recalculation:** entering/updating results recomputes scores (feature 12), idempotently.

## Acceptance criteria
- Non-admin users cannot reach the page or perform any of its writes.
- A full tournament can be driven end-to-end: lock group picks → enter group results + R32 field → users pick R32 → enter R32 results + R16 field → … → Final.
- Re-entering a corrected result updates scores without double-counting.

## TODO
- Exact admin UX/layout and input validation.
- Confirmation guards on destructive edits (e.g. overwriting a populated round).
- Whether recalculation is automatic on save or a manual "recalculate" button.