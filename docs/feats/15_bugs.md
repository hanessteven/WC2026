# 15 — Bug Backlog (found by the test suite)

**Status:** ✅ All resolved (BUG-1…6 + minor note).
**Source:** issues surfaced while building feature 14 ([14_test_suite.md](14_test_suite.md)).
**How to use:** tackle one entry at a time, top-down. Each has a repro, the root cause, and a
suggested fix. When a bug is fixed, flip its heading to ✅ and turn its `xfail` test into a normal
regression guard (BUG-1 has been done this way).

Legend: 🔴 functional · 🟠 robustness · 🟡 minor / cosmetic / doc

---

## BUG-1 🟠 — One corrupt category zeroes a user's entire score — ✅ FIXED
**Where:** `src/scoring.py::calculate_scores` / `score_group_stage`.
**Repro (now a regression guard):** `tests/test_score_runner.py::test_corrupt_group_should_not_wipe_bracket_points`.
A user with a **valid** bracket pick (worth 1) plus **one** malformed group row (e.g. a
`predicted_ranking` of length 3) used to end up with `bracket_pts == 0` and `total_pts == 0`.
**Root cause:** `_build_user_predictions` uses `model_construct()` to bypass validation precisely
so scoring is "robust on edge cases," but `calculate_scores` then indexed `predicted_ranking[pos]`
for `pos in range(4)` → `IndexError`. The runner's broad `except Exception` swallowed it and wrote
**all-zero** for that user, wiping the categories that were perfectly valid.
**Fix:** scoring is now resilient at two levels via a `_safe(fn, label, default=0)` wrapper in
`src/scoring.py`:
- `calculate_scores` scores each of the five categories independently, so a failure in one
  contributes 0 without affecting the others;
- `score_group_stage` scores each group in isolation, so one corrupt group doesn't zero the rest.

Swallowed exceptions are logged at WARNING (with traceback) via a module logger, so degradation is
observable rather than silent. The runner keeps its per-user net only as a last resort for the case
where a user's predictions can't be *built* at all (e.g. a malformed UUID).

---

## BUG-2 🟡 — Two divergent code paths for "is this category locked?" — ✅ FIXED
**Where:** `src/predictions.py::is_locked` (was an uncached live query) vs
`src/admin.py::load_lock_state` (`@st.cache_data(ttl=30)`).
**Issue:** the same `lock_state` table was read two different ways with two freshness semantics.
**Fix:** `is_locked` now delegates to the single cached source —
`return bool(load_lock_state().get(category, False))`. `set_lock` already clears that cache, so all
callers (user pages and admin) see the same value with no staleness window.

---

## BUG-3 🟡 — Stale golden-boot rule in the feat 12 spec — ✅ FIXED
**Where:** `docs/feats/12_scoring_engine.md`.
**Issue:** the spec said *"Golden boot: points per goal by drafted players,"* contradicting the
finalized rule in `scoring_rules.md`, feature 08, and the code (flat **7 pts if any drafted player
is the top scorer**).
**Fix:** the feat 12 line now states the flat-7-pts Golden Boot rule and points to
`scoring_rules.md`. Doc-only; no code change.

---

## BUG-4 🟢 — (Fixed during test hardening) leaderboard assumed embedded profile is a dict
**Where:** `src/predictions.py::load_leaderboard`.
**Issue:** the old code did `r.get("profiles") or {}` then `profile.get(...)`. supabase-py can
return an embedded to-one resource as a **single-item list** depending on relationship detection;
that path would raise `AttributeError`. **Already addressed** by extracting `_assemble_leaderboard`
+ `_embedded_profile` (normalizes dict-or-list) and covering it with
`tests/test_predictions_db.py::test_leaderboard_handles_embedded_profile_as_list`. Listed here for
the record; no further action needed unless we revert the refactor.

---

## BUG-5 🟡 — Editing a prediction after its result is entered leaves a stale score — ✅ FIXED
**Where:** the `save_*` helpers in `src/predictions.py` (group, champion, golden boot, bracket,
bonus) — none triggered a recalc.
**Issue:** scores only recomputed on **admin result** saves, so a user editing a still-unlocked
prediction after a result existed kept a stale score until the next admin save.
**Fix:** added `src/score_runner.py::recalculate_user_score(user_id)` (a single-user recompute that
shares `_score_row_for_user` with the bulk recalc) and call it at the end of every user save. A
user's standing now refreshes the instant they save, regardless of result-entry timing — and they
appear on the leaderboard as soon as they make their first pick.
**Guard:** `tests/test_predictions_db.py::test_save_prediction_recomputes_score_without_admin_recalc`.

---

## BUG-6 🟡 — Champion pick allows `dark_horse == champion` — ✅ FIXED
**Where:** `src/models.py::ChampionPick` and `src/predictions.py::save_champion_pick`.
**Issue:** the model and the save path didn't stop a user naming the same team as both champion and
dark horse (16 pts for one team), even though the UI already warned against it.
**Fix:** added a `ChampionPick` `model_validator` requiring `dark_horse != champion`, and
`save_champion_pick` now constructs a `ChampionPick` before writing so the rule is enforced at the
data boundary, not just in the page. (Dark-horse *eligibility* — `is_dark_horse_eligible` — remains
enforced in the UI, which only offers eligible teams.)
**Guards:** `tests/test_models_extra.py::test_champion_pick_rejects_dark_horse_equal_to_champion`
and `tests/test_predictions_db.py::test_save_champion_pick_rejects_dark_horse_equal_to_champion`.

---

## Minor notes
- ✅ `src/predictions.py::load_bonus_questions` docstring now lists `correct_options` (previously
  omitted, though the query already selected it).