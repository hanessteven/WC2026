# 08 — Golden Boot Salary-Cap Draft

**Status:** 🔲 Not started
**Depends on:** 03, 04, 05

## Goal
A budget-constrained draft where users pick multiple golden-boot candidates from a
tiered, priced list without exceeding a fixed $100 budget.

## Requirements
- Display the seeded player list (feature 04), grouped by tier, with costs.
- User drafts multiple players; a **running total** shows spend vs the **$100 budget**.
- **Cannot save a roster over budget** (validated on submit).
- Save & edit freely until the `golden_boot` lock (feature 10); read-only when locked.
- **Seeded list only** — no write-in players. Admin can extend the list via the seed YAML.

## Scoring (see [../scoring_rules.md](../scoring_rules.md))
- **7 pts** if any drafted player wins the Golden Boot (top scorer of the tournament).
- If multiple players tie for the Golden Boot, any user who drafted one of the tied
  winners receives 7 pts.
- No per-goal points — the draft is purely about predicting who will be top scorer.

## Pricing intent
Top favourites are priced to consume the majority of the budget:
- Mbappé ($65) = 65% of budget — you can draft him but afford little else.
- Kane ($55) + Haaland ($50) = $105 — can't combine the two biggest non-Mbappé names.
- Skipping the top tier frees up budget for 3–5 mid-range picks as a spread strategy.

## Acceptance criteria
- Cannot submit a roster over $100 budget.
- Roster persists, edits work, locks correctly when `golden_boot` is locked.
- Players are displayed grouped by tier with name, team, flag, and cost.
- Running budget total updates live as the user checks/unchecks players.
- A player that would push the roster over budget is visually flagged.