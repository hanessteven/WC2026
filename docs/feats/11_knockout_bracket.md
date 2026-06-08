# 11 — Wave-Based Knockout Bracket

**Status:** 🔲 Not started
**Depends on:** 10 (admin populates real matchups), 03, 05

## Goal
Let users pick winners round-by-round from the **actual** matchups the admin enters, rather than a self-seeded full bracket. Everyone picks from the same real board each round.

## Requirements
- Show the **currently open round's real matchups** (from `real_bracket`, populated by feature 10).
- User picks a **winner per match** in the open round.
- **Per-round locking:** a round becomes read-only when its lock is set (feature 10) — typically before that round kicks off.
- **Past rounds:** read-only, showing each pick's correctness against results.
- **Future rounds:** hidden until the admin populates them.
- The upfront champion pick (feature 07) is shown separately, not re-picked here.

## Scoring impact (see [../scoring_rules.md](../scoring_rules.md))
- Exact per-match winner, weighted by round (Fibonacci): R32=1, R16=2, QF=3, SF=5, Final=8.

## Acceptance criteria
- A round opens for picking only after the admin populates it and before its lock.
- Picks persist and lock per round.
- After results are entered, correct/incorrect picks render clearly.

## TODO
- Confirm behavior when a user misses a round entirely (zero points for that round — confirm this is the intended consequence).
- Visual layout of the round (list of matchups vs bracket-style tree).