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
- Correct champion: **13 pts** (Fibonacci step above the 8pt Final bracket pick).
- Correct dark horse: **3 pts** if the team reaches the **quarterfinals or further** (top 8).

## Acceptance criteria
- Pick persists and loads pre-filled on return visits.
- Locked when the `champion` category is locked — shown read-only, no save button.
- Distinct from the in-bracket Final pick (which is scored separately per round).
- Champion and dark horse cannot be the same team.
- Dark horse is optional; saving with no dark horse pick is valid.