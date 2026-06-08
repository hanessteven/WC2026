# 08 — Golden Boot Salary-Cap Draft

**Status:** 🔲 Not started
**Depends on:** 03, 04, 05

## Goal
A budget-constrained "money draft" where users select multiple golden-boot candidates from a tiered, priced list without exceeding a fixed budget.

## Requirements
- Display the seeded player list (feature 04) with tier costs.
- User drafts multiple players; a **running total** shows spend against the **\$100 budget** (configurable).
- The form **prevents exceeding budget** (validation + clear messaging).
- Save & edit until the `golden_boot` lock (feature 10); read-only when locked.

## Scoring impact (see [../scoring_rules.md](../scoring_rules.md))
- Points per goal scored by each drafted player (1 pt/goal baseline).
- TODO: confirm whether to add a bonus if a drafted player is the actual Golden Boot winner.

## Acceptance criteria
- Cannot submit a roster over budget.
- Roster persists, edits work, locks correctly.

## TODO
- Confirm final scoring (per-goal only vs per-goal + winner bonus).
- Decide whether write-in players are allowed or only the seeded list.