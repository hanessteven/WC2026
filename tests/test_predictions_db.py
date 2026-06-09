"""Unit + integration tests for src/predictions.py.

Unit: the pure _assemble_leaderboard ranking helper.
Integration: read transforms and save->cache-clear round-trips via the fake DB.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.predictions import (
    _assemble_leaderboard,
    is_locked,
    load_bonus_answers,
    load_bracket_matchups,
    load_bracket_picks,
    load_champion_pick,
    load_golden_boot_picks,
    load_group_predictions,
    load_players_by_tier,
    load_teams_by_group,
    save_bracket_picks,
    save_champion_pick,
    save_golden_boot_picks,
    save_group_predictions,
)

U1 = str(uuid4())
U2 = str(uuid4())


def _raw(user_id, name, total, **cats):
    return {
        "user_id": user_id,
        "total_pts": total,
        "group_stage_pts": cats.get("group", 0),
        "bracket_pts": cats.get("bracket", 0),
        "champion_pts": cats.get("champion", 0),
        "golden_boot_pts": cats.get("boot", 0),
        "bonus_pts": cats.get("bonus", 0),
        "profiles": {"display_name": name, "email": f"{name}@t.com"},
    }


# ── _assemble_leaderboard (pure) ─────────────────────────────────────────────

def test_leaderboard_sorted_by_total_desc():
    rows = _assemble_leaderboard([
        _raw("a", "Ann", 10), _raw("b", "Bea", 30), _raw("c", "Cal", 20),
    ])
    assert [r["display_name"] for r in rows] == ["Bea", "Cal", "Ann"]
    assert [r["rank"] for r in rows] == [1, 2, 3]


def test_leaderboard_ties_share_rank_then_skip():
    rows = _assemble_leaderboard([
        _raw("a", "Ann", 30), _raw("b", "Bea", 30), _raw("c", "Cal", 10),
    ])
    # Two at 30 share rank 1; next distinct total is rank 3 (standard competition ranking).
    assert [(r["display_name"], r["rank"]) for r in rows] == [
        ("Ann", 1), ("Bea", 1), ("Cal", 3),
    ]


def test_leaderboard_tie_breaks_alphabetically():
    rows = _assemble_leaderboard([
        _raw("a", "Zoe", 30), _raw("b", "Amy", 30),
    ])
    assert [r["display_name"] for r in rows] == ["Amy", "Zoe"]
    assert all(r["rank"] == 1 for r in rows)


def test_leaderboard_coalesces_nulls():
    rows = _assemble_leaderboard([
        {"user_id": "a", "total_pts": None, "group_stage_pts": None,
         "bracket_pts": None, "champion_pts": None, "golden_boot_pts": None,
         "bonus_pts": None, "profiles": None},
    ])
    r = rows[0]
    assert r["total_pts"] == 0 and r["display_name"] == "" and r["email"] == ""
    assert r["rank"] == 1


def test_leaderboard_handles_embedded_profile_as_list():
    """supabase-py can hand back the embedded resource as a single-item list."""
    rows = _assemble_leaderboard([
        {"user_id": "a", "total_pts": 5, "profiles": [{"display_name": "Liz", "email": "l@t.com"}]},
    ])
    assert rows[0]["display_name"] == "Liz"
    assert rows[0]["email"] == "l@t.com"


def test_leaderboard_empty():
    assert _assemble_leaderboard([]) == []


# ── read transforms (integration) ────────────────────────────────────────────

def test_load_teams_by_group_groups_and_orders(fake_db):
    fake_db.seed("seed_teams", [
        {"id": 2, "name": "Mexico", "group_letter": "A", "flag_emoji": "🇲🇽", "is_dark_horse_eligible": True},
        {"id": 1, "name": "USA", "group_letter": "A", "flag_emoji": "🇺🇸", "is_dark_horse_eligible": True},
        {"id": 3, "name": "Brazil", "group_letter": "B", "flag_emoji": "🇧🇷", "is_dark_horse_eligible": True},
    ])
    groups = load_teams_by_group()
    assert set(groups) == {"A", "B"}
    assert [t["name"] for t in groups["A"]] == ["USA", "Mexico"]   # ordered by id
    assert [t["name"] for t in groups["B"]] == ["Brazil"]


def test_load_players_by_tier_orders_by_cost_desc(fake_db):
    fake_db.seed("seed_players", [
        {"id": 1, "name": "Cheap", "team_name": "T", "tier": 1, "cost": 10},
        {"id": 2, "name": "Pricey", "team_name": "T", "tier": 1, "cost": 60},
        {"id": 3, "name": "Mid", "team_name": "T", "tier": 2, "cost": 30},
    ])
    tiers = load_players_by_tier()
    assert [p["name"] for p in tiers[1]] == ["Pricey", "Cheap"]   # desc by cost
    assert [p["name"] for p in tiers[2]] == ["Mid"]


def test_load_group_predictions_keyed_by_group(fake_db):
    fake_db.seed("predictions_group_stage", [
        {"user_id": U1, "group_letter": "A", "predicted_ranking": ["a", "b", "c", "d"],
         "third_place_advances": True},
        {"user_id": U2, "group_letter": "A", "predicted_ranking": ["x", "y", "z", "w"],
         "third_place_advances": False},
    ])
    out = load_group_predictions(U1)
    assert set(out) == {"A"}
    assert out["A"]["predicted_ranking"] == ["a", "b", "c", "d"]


def test_load_champion_pick_none_when_absent(fake_db):
    assert load_champion_pick(U1) is None


def test_load_bracket_matchups_grouped_by_round_ordered_by_slot(fake_db):
    fake_db.seed("real_bracket", [
        {"id": 2, "round": "R32", "slot": 2, "team_a": "C", "team_b": "D", "winner": None, "is_penalty": False},
        {"id": 1, "round": "R32", "slot": 1, "team_a": "A", "team_b": "B", "winner": None, "is_penalty": False},
        {"id": 3, "round": "QF", "slot": 1, "team_a": "E", "team_b": "F", "winner": None, "is_penalty": False},
    ])
    out = load_bracket_matchups()
    assert list(out) == ["QF", "R32"] or set(out) == {"R32", "QF"}
    assert [m["slot"] for m in out["R32"]] == [1, 2]   # ordered by slot


def test_load_bracket_picks_map(fake_db):
    fake_db.seed("predictions_bracket", [
        {"user_id": U1, "matchup_id": 101, "predicted_winner": "X"},
        {"user_id": U1, "matchup_id": 102, "predicted_winner": "Y"},
    ])
    assert load_bracket_picks(U1) == {101: "X", 102: "Y"}


def test_load_bonus_answers_map(fake_db):
    fake_db.seed("predictions_bonus", [
        {"user_id": U1, "question_id": 1, "chosen_option": "USA"},
    ])
    assert load_bonus_answers(U1) == {1: "USA"}


# ── lock state ────────────────────────────────────────────────────────────────

def test_is_locked_true_false_and_missing(fake_db):
    fake_db.seed("lock_state", [
        {"category": "group_stage", "is_locked": True},
        {"category": "bonus", "is_locked": False},
    ])
    assert is_locked("group_stage") is True
    assert is_locked("bonus") is False
    assert is_locked("champion") is False   # no row at all


# ── save -> cache-clear round trips (integration) ────────────────────────────

def test_save_champion_then_reload_reflects_change(fake_db):
    assert load_champion_pick(U1) is None        # warms the cache with None
    save_champion_pick(U1, "Brazil", "Japan")    # writes + clears cache
    pick = load_champion_pick(U1)
    assert pick is not None
    assert pick["champion"] == "Brazil"
    assert pick["dark_horse"] == "Japan"


def test_save_champion_upsert_overwrites(fake_db):
    save_champion_pick(U1, "Brazil", None)
    save_champion_pick(U1, "France", "Morocco")
    assert len([r for r in fake_db.rows("predictions_champion") if r["user_id"] == U1]) == 1
    pick = load_champion_pick(U1)
    assert pick["champion"] == "France" and pick["dark_horse"] == "Morocco"


def test_save_golden_boot_replaces_previous_picks(fake_db):
    save_golden_boot_picks(U1, [1, 2])
    assert load_golden_boot_picks(U1) == {1, 2}
    save_golden_boot_picks(U1, [3, 4])
    assert load_golden_boot_picks(U1) == {3, 4}


def test_save_golden_boot_empty_clears_all(fake_db):
    save_golden_boot_picks(U1, [1, 2])
    save_golden_boot_picks(U1, [])
    assert load_golden_boot_picks(U1) == set()


def test_save_bracket_picks_upsert(fake_db):
    save_bracket_picks(U1, {101: "X", 102: "Y"})
    assert load_bracket_picks(U1) == {101: "X", 102: "Y"}
    save_bracket_picks(U1, {101: "Z"})   # change one
    assert load_bracket_picks(U1)[101] == "Z"
    # Still only one row for (U1, 101)
    pair = [r for r in fake_db.rows("predictions_bracket")
            if r["user_id"] == U1 and r["matchup_id"] == 101]
    assert len(pair) == 1


# ── BUG-5: a user save recomputes that user's score immediately ──────────────

def test_save_prediction_recomputes_score_without_admin_recalc(fake_db):
    """Editing a prediction when a result already exists refreshes the score on the spot."""
    fake_db.seed("results_group_stage", [
        {"group_letter": "A", "final_ranking": ["A1", "A2", "A3", "A4"],
         "third_place_advances": True},
    ])
    save_group_predictions(U1, [
        {"user_id": U1, "group_letter": "A",
         "predicted_ranking": ["A1", "A2", "A3", "A4"], "third_place_advances": True},
    ])
    row = next(r for r in fake_db.rows("scores") if r["user_id"] == U1)
    assert row["group_stage_pts"] == 8
    assert row["total_pts"] == 8


# ── BUG-6: champion validation enforced at the save boundary ─────────────────

def test_save_champion_pick_rejects_dark_horse_equal_to_champion(fake_db):
    with pytest.raises(ValueError, match="different team"):
        save_champion_pick(U1, "Brazil", "Brazil")
    # Nothing was written.
    assert fake_db.rows("predictions_champion") == []