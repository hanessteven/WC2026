# 10 — Admin Panel (Results, Locks, Bracket Progression)

**Status:** 🔲 Not started
**Depends on:** 02, 03, 05 (admin auth)

## Goal
An admin-only page where you drive the tournament: toggle locks, enter results nightly, populate each knockout round's real matchups, trigger score recalculation, and manage user accounts.

## Requirements (admin-only; gated by `is_admin`)

### Lock controls
Per-category + per-round toggles — `group_stage`, `champion`, `golden_boot`, `bonus`, and each knockout round (`R32`, `R16`, `QF`, `SF`, `Final`). Flipping a lock makes that surface read-only for users.

### Group results
Enter final standings per group + which 8 third-place teams advanced.

### Bracket progression (drives the wave bracket, feature 11)
- After the group stage, enter the **real Round of 32 matchups** → populates the R32 bracket users pick from.
- After each round's results, enter the **next round's real matchups**.

### Match results
Per knockout match, record winner (+ penalty-decided flag).

### Golden boot goals
Record goals scored per player.

### Bonus answers
Record the correct option(s) per question — supporting **multiple correct** for ties.

### Score recalculation
Entering/updating results recomputes scores (feature 12), idempotently.

### Reset a user's picks
Admin can wipe all prediction data for a specific user and return them to a clean slate (all tables: `predictions_group_stage`, `predictions_champion`, `predictions_bracket`, `predictions_golden_boot`, `predictions_bonus`).

- **Select user:** admin chooses from a dropdown of all registered users (by display name / email).
- **Confirmation gate:** before processing, show a warning — e.g. *"This will permanently delete all picks for [display name]. This cannot be undone."* — and require the admin to click a second **"Yes, reset"** button to proceed.
- **Scope:** deletes all rows in all five prediction tables for that user. Does not delete the user's profile or account.
- **Use case:** a user forgot their password and needs to re-register (which would create a new profile ID), or a user wants a full do-over before the lock date.

## Acceptance criteria
- Non-admin users cannot reach the page or perform any of its writes.
- A full tournament can be driven end-to-end: lock group picks → enter group results + R32 field → users pick R32 → enter R32 results + R16 field → … → Final.
- Re-entering a corrected result updates scores without double-counting.
- An admin can reset any user's picks; a two-step confirmation (select → warning → confirm) is required before any data is deleted.
- A non-admin cannot trigger a reset (enforced at both the UI and DB layer via service-role writes).

## TODO
- Exact admin UX/layout and input validation.
- Confirmation guards on destructive edits (e.g. overwriting a populated round).
- Whether recalculation is automatic on save or a manual "recalculate" button.