"""Integration tests for src/admin.py against the fake Supabase client.

Verifies lock toggles, that result saves trigger a recalc, and that the
user-reset wipes every prediction table.
"""
from __future__ import annotations

from uuid import uuid4

from src.admin import (
    load_golden_boot_result_lock,
    load_group_result_locks,
    load_group_results,
    load_lock_state,
    load_player_goals,
    load_real_bracket,
    reset_user_picks,
    save_bonus_correct_options,
    save_bracket_round,
    save_group_results,
    save_match_results,
    save_player_goals,
    set_golden_boot_result_lock,
    set_group_result_lock,
    set_lock,
)

U1 = str(uuid4())
U2 = str(uuid4())

CATEGORIES = ["group_stage", "champion", "golden_boot", "bonus",
              "R32", "R16", "QF", "SF", "F"]


def _seed_locks(db):
    db.seed("lock_state", [{"category": c, "is_locked": False} for c in CATEGORIES])


def _score_row(db, user_id):
    return next((r for r in db.rows("scores") if r["user_id"] == user_id), None)


# ── locks ─────────────────────────────────────────────────────────────────────

def test_set_lock_toggles_state(fake_db, monkeypatch):
    monkeypatch.setattr("src.auth.get_current_user", lambda: {"email": "admin@test.com"})
    monkeypatch.setattr("src.locks.get_current_user", lambda: {"email": "admin@test.com"})
    _seed_locks(fake_db)

    set_lock("group_stage", True)
    state = load_lock_state()
    assert state["group_stage"] is True
    assert state["bonus"] is False

    set_lock("group_stage", False)
    assert load_lock_state()["group_stage"] is False


# ── group results -> recalc ────────────────────────────────────────────────

def test_save_group_results_persists_and_recalculates(fake_db):
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("predictions_group_stage", [
        {"user_id": U1, "group_letter": "A",
         "predicted_ranking": ["A1", "A2", "A3", "A4"], "third_place_advances": True},
    ])
    save_group_results([
        {"group_letter": "A", "final_ranking": ["A1", "A2", "A3", "A4"],
         "third_place_advances": True},
    ])

    assert load_group_results()["A"]["final_ranking"] == ["A1", "A2", "A3", "A4"]
    assert _score_row(fake_db, U1)["group_stage_pts"] == 8


# ── bracket round + match results -> recalc ─────────────────────────────────

def test_save_bracket_round_upserts(fake_db):
    save_bracket_round("R32", [
        {"slot": 1, "team_a": "A", "team_b": "B"},
        {"slot": 2, "team_a": "C", "team_b": "D"},
    ])
    bracket = load_real_bracket()
    assert {r["slot"] for r in bracket} == {1, 2}
    assert all(r["round"] == "R32" for r in bracket)
    # No result recorded yet. (The fake doesn't model DB column defaults, so the
    # winner key may simply be absent rather than explicitly NULL — .get() covers both.)
    assert all(r.get("winner") is None for r in bracket)


def test_save_match_results_sets_winner_and_recalculates(fake_db):
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("real_bracket", [
        {"id": 101, "round": "R32", "slot": 1, "team_a": "X", "team_b": "Y",
         "winner": None, "is_penalty": False},
    ])
    fake_db.seed("predictions_bracket", [
        {"user_id": U1, "matchup_id": 101, "predicted_winner": "X"},
    ])

    save_match_results([{"id": 101, "winner": "X", "is_penalty": False}])

    updated = next(r for r in fake_db.rows("real_bracket") if r["id"] == 101)
    assert updated["winner"] == "X"
    assert _score_row(fake_db, U1)["bracket_pts"] == 1


# ── player goals -> recalc ──────────────────────────────────────────────────

def test_save_player_goals_replaces_and_drops_zero(fake_db):
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("seed_players", [
        {"id": 10, "name": "Striker", "cost": 50},
        {"id": 11, "name": "Other", "cost": 40},
    ])
    fake_db.seed("results_player_goals", [{"player_id": 10, "goals_scored": 2}])

    save_player_goals({10: 3, 11: 0})

    goals = load_player_goals()
    assert goals == {10: 3}          # 11 had 0 goals -> dropped
    assert _score_row(fake_db, U1) is not None   # recalc ran


# ── bonus correct options -> recalc ─────────────────────────────────────────

def test_save_bonus_correct_options_scores_matching_users(fake_db):
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("bonus_question_defs", [
        {"id": 1, "question_text": "Q", "valid_options": ["USA", "Mexico"],
         "correct_options": None, "point_value": 2},
    ])
    fake_db.seed("predictions_bonus", [
        {"user_id": U1, "question_id": 1, "chosen_option": "USA"},
    ])

    save_bonus_correct_options(1, ["USA"])

    defrow = next(r for r in fake_db.rows("bonus_question_defs") if r["id"] == 1)
    assert defrow["correct_options"] == ["USA"]
    assert _score_row(fake_db, U1)["bonus_pts"] == 2


def test_save_bonus_correct_options_tie_awards_all(fake_db):
    """A tie: two correct options; users who picked either get the points."""
    fake_db.seed("profiles", [
        {"id": U1, "email": "a@t.com", "display_name": "A"},
        {"id": U2, "email": "b@t.com", "display_name": "B"},
    ])
    fake_db.seed("bonus_question_defs", [
        {"id": 1, "question_text": "Q", "valid_options": ["USA", "Mexico", "Canada"],
         "correct_options": None, "point_value": 2},
    ])
    fake_db.seed("predictions_bonus", [
        {"user_id": U1, "question_id": 1, "chosen_option": "USA"},
        {"user_id": U2, "question_id": 1, "chosen_option": "Mexico"},
    ])

    save_bonus_correct_options(1, ["USA", "Mexico"])

    assert _score_row(fake_db, U1)["bonus_pts"] == 2
    assert _score_row(fake_db, U2)["bonus_pts"] == 2


# ── reset user picks ──────────────────────────────────────────────────────────

def test_reset_user_picks_wipes_only_that_user(fake_db):
    tables = ["predictions_group_stage", "predictions_champion",
              "predictions_bracket", "predictions_golden_boot", "predictions_bonus"]
    for t in tables:
        fake_db.seed(t, [{"user_id": U1, "x": 1}, {"user_id": U2, "x": 2}])

    reset_user_picks(U1)

    for t in tables:
        remaining = fake_db.rows(t)
        assert all(r["user_id"] != U1 for r in remaining), f"{t} still has U1"
        assert any(r["user_id"] == U2 for r in remaining), f"{t} lost U2"


# ── results finalization (locking) ────────────────────────────────────────────

def test_load_group_result_locks_default_false(fake_db):
    groups = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    fake_db.seed("results_group_lock", [{"group_letter": g, "is_locked": False} for g in groups])
    locks = load_group_result_locks()
    assert all(not locked for locked in locks.values())


def test_set_group_result_lock_toggles_state(fake_db):
    groups = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    fake_db.seed("results_group_lock", [{"group_letter": g, "is_locked": False} for g in groups])

    set_group_result_lock("A", True)
    locks = load_group_result_locks()
    assert locks["A"] is True
    assert locks["B"] is False

    set_group_result_lock("A", False)
    locks = load_group_result_locks()
    assert locks["A"] is False


def test_load_golden_boot_result_lock_default_false(fake_db):
    fake_db.seed("results_golden_boot_lock", [{"id": 1, "is_locked": False}])
    locked = load_golden_boot_result_lock()
    assert locked is False


def test_set_golden_boot_result_lock_toggles_state(fake_db):
    fake_db.seed("results_golden_boot_lock", [{"id": 1, "is_locked": False}])

    set_golden_boot_result_lock(True)
    locked = load_golden_boot_result_lock()
    assert locked is True

    set_golden_boot_result_lock(False)
    locked = load_golden_boot_result_lock()
    assert locked is False