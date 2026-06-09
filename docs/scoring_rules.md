# Scoring Rules (Fibonacci-Weighted)

All point values are **configurable** (kept in a single source so they can be tuned without scattered code changes).

## Group Stage
| Category | Points |
| :--- | :--- |
| Correct Group Qualifier (top 2) | 1 per team |
| Correct Group Exact Position (bonus) | 1 per team |
| Correct 3rd Place Advancer | 2 per team |

## Knockout Bracket (Wave-Based, Exact Match)
The bracket is **wave-based**: every user picks winners from the *same actual matchups* the admin enters each round, so scoring is an **exact per-match** check, weighted by round.

| Round | Points (per correct winner) |
| :--- | :--- |
| Round of 32 | 1 |
| Round of 16 | 2 |
| Quarterfinal | 3 |
| Semifinal | 5 |
| Final (winner = champion) | 8 |

## Upfront Predictions
Made before kickoff, locked at tournament start — separate from the in-bracket Final pick.

| Pick | Points |
| :--- | :--- |
| Correct Champion (upfront) | 13 |
| Correct Dark Horse (reaches QF or further) | 3 |

## Draft & Bonuses
| Category | Points |
| :--- | :--- |
| Golden Boot (per goal by a drafted player) | 1 |
| Bonus Question Correct | 2 |

## Calculation Strategy
- Scoring engine accepts two objects: `UserPredictions` and `TournamentResults`; returns a `ScoringBreakdown`.
- All scoring functions return an integer total for the specific category.
- **Partial Tournament Data:** the engine must gracefully handle incomplete results — score only the rounds/categories with results available, updating incrementally as new results arrive. Scoring must be **idempotent** (recomputing yields the same result; no double-counting on re-entry).
- **Tie Handling in Bonus Questions:** when a bonus outcome ties, the admin records multiple correct options and **all** users who picked any correct option receive full points.