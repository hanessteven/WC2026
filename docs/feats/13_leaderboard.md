# 13 — Leaderboard & Standings

**Status:** 🔲 Not started
**Depends on:** 12

## Goal
The social payoff: a live leaderboard ranking everyone by total points, with per-category breakdowns and per-user detail.

## Requirements
- **Leaderboard:** all users ranked by total score (from feature 12 output).
- **Breakdown:** show per-category points (group, bracket, champion, golden boot, bonus).
- **Per-user detail:** drill into one user's predictions vs results.
- **Caching:** wrap DB reads in `st.cache_data`; refresh after the admin enters new results.
- **Tie display:** clearly show shared ranks.

## Acceptance criteria
- Rankings match the scoring engine's output.
- Standings update after a nightly results entry (cache invalidates appropriately).

## TODO
- Tiebreak/sort rules for display (e.g. how to order equal totals).
- Optional "Top Dawg" per-category awards from the original brief (group-stage leader, golden-boot flop, etc.).