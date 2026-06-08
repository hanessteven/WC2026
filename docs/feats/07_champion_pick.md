# 07 — Upfront Champion Pick

**Status:** 🔲 Not started
**Depends on:** 03, 05

## Goal
A single high-value, long-range prediction made **before the tournament starts**: who wins it all (plus an optional dark-horse pick). Preserves "called it from day one" bragging rights alongside the wave-based bracket.

## Requirements
- User picks a **champion** from the 48 teams, and optionally a **dark horse**.
- Locked at tournament start under its own lock category (`champion`), independent of the per-round bracket locks.
- Lightweight UI; one selection (+ optional second).

## Scoring impact (see [../scoring_rules.md](../scoring_rules.md))
- Correct champion: large fixed reward (TODO: confirm value; suggested 13).
- Correct dark horse: bonus (TODO: confirm value and what "dark horse correct" means — e.g. reaches semifinal).

## Acceptance criteria
- Pick persists and locks at tournament start.
- Distinct from the in-bracket Final pick (which is scored separately per round).

## TODO
- Confirm champion / dark-horse point values.
- Define the dark-horse success condition.