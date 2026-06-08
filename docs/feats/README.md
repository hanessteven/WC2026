# Feature Roadmap

Build features in numbered order. Each spec is self-contained and lists its dependencies, requirements, and acceptance criteria. Items marked `TODO:` are intentionally deferred for a later session/model to finalize.

## Status legend
- 🔲 Not started
- 🚧 In progress
- ✅ Done

## Roadmap

| # | Feature | Depends on | Status |
|---|---------|-----------|--------|
| 01 | [Project Scaffolding & Configuration](01_project_scaffolding.md) | — | ✅ |
| 02 | [Database Schema & RLS Policies](02_database_schema_rls.md) | 01 | ✅ |
| 03 | [Data Models (Pydantic)](03_data_models.md) | 02 | ✅ |
| 04 | [Seed Data](04_seed_data.md) | 02, 03 | ✅ |
| 05 | [Authentication (Magic Link + Whitelist)](05_authentication.md) | 01, 02 | 🔲 |
| 06 | [Group Stage Predictions](06_group_stage_predictions.md) | 03, 04, 05 | 🔲 |
| 07 | [Upfront Champion Pick](07_champion_pick.md) | 03, 05 | 🔲 |
| 08 | [Golden Boot Salary-Cap Draft](08_golden_boot_draft.md) | 03, 04, 05 | 🔲 |
| 09 | [Bonus Questions](09_bonus_questions.md) | 03, 04, 05 | 🔲 |
| 10 | [Admin Panel (Results, Locks, Bracket Progression)](10_admin_panel.md) | 02, 03, 05 | 🔲 |
| 11 | [Wave-Based Knockout Bracket](11_knockout_bracket.md) | 10, 03, 05 | 🔲 |
| 12 | [Scoring Engine](12_scoring_engine.md) | 03, 06–11 | 🔲 |
| 13 | [Leaderboard & Standings](13_leaderboard.md) | 12 | 🔲 |

## Dependency notes
- **01–04 are the foundation** (scaffolding → schema → models → seed). Don't start prediction UIs until these exist.
- **05 (auth)** gates every user-facing prediction page.
- **06–09** are independent prediction surfaces and can be built in any order once 03–05 exist.
- **11 (wave bracket) depends on 10 (admin)** because the admin enters each round's real matchups, which populate the bracket users pick from.
- **12 (scoring) is the heart** — pure Python, fully unit-tested with fixtures before real data exists. It depends conceptually on all prediction shapes being defined.
- **13 (leaderboard)** is the final read-only surface over scoring output.

## Bracket model (decided)
Wave-based: users lock group picks at group-stage kickoff; the admin enters the real Round of 32 field once groups finish; the bracket page then opens that round for everyone to pick from the *same actual matchups*. Repeat per round. A separate **upfront champion pick** (feature 07) locks at tournament start for long-range bragging rights.