"""Integration tests for src/score_runner.py against the fake Supabase client.

Exercises the full flow: predictions + results in the DB -> calculate_scores ->
scores table upsert. No network, no real DB.
"""
from __future__ import annotations

from uuid import uuid4

from src.score_runner import recalculate_all_scores

U1 = str(uuid4())
U2 = str(uuid4())


def _seed_full_tournament(db, *, user_id: str = U1) -> None:
    """A complete, internally-consistent tournament where `user_id` predicts everything right."""
    db.seed("profiles", [
        {"id": user_id, "email": "alice@test.com", "display_name": "Alice"},
        {"id": U2, "email": "bob@test.com", "display_name": "Bob"},  # no predictions
    ])

    # Group A — user ranks it exactly right and calls its 3rd-place advancer.
    db.seed("results_group_stage", [
        {"group_letter": "A", "final_ranking": ["A1", "A2", "A3", "A4"],
         "third_place_advances": True},
    ])
    db.seed("predictions_group_stage", [
        {"user_id": user_id, "group_letter": "A",
         "predicted_ranking": ["A1", "A2", "A3", "A4"], "third_place_advances": True},
    ])

    # Knockout: one R32, one QF (establishes dark horse), one Final.
    db.seed("real_bracket", [
        {"id": 101, "round": "R32", "slot": 1, "team_a": "X", "team_b": "Y",
         "winner": "X", "is_penalty": False},
        {"id": 201, "round": "QF", "slot": 1, "team_a": "DarkHorse", "team_b": "Z",
         "winner": "DarkHorse", "is_penalty": False},
        {"id": 301, "round": "F", "slot": 1, "team_a": "Champ", "team_b": "Runner",
         "winner": "Champ", "is_penalty": False},
    ])
    db.seed("predictions_bracket", [
        {"user_id": user_id, "matchup_id": 101, "predicted_winner": "X"},
        {"user_id": user_id, "matchup_id": 201, "predicted_winner": "DarkHorse"},
        {"user_id": user_id, "matchup_id": 301, "predicted_winner": "Champ"},
    ])

    # Champion pick: correct champion + dark horse that reached QF.
    db.seed("predictions_champion", [
        {"user_id": user_id, "champion": "Champ", "dark_horse": "DarkHorse"},
    ])

    # Golden boot: drafted player is the sole top scorer.
    db.seed("seed_players", [
        {"id": 10, "name": "Striker", "cost": 50},
        {"id": 11, "name": "Bench", "cost": 5},
    ])
    db.seed("results_player_goals", [
        {"player_id": 10, "goals_scored": 5},
        {"player_id": 11, "goals_scored": 1},
    ])
    db.seed("predictions_golden_boot", [
        {"user_id": user_id, "player_id": 10},
    ])

    # Bonus: one question answered correctly.
    db.seed("bonus_question_defs", [
        {"id": 1, "question_text": "Q1", "valid_options": ["USA", "Mexico"],
         "correct_options": ["USA"], "point_value": 2},
    ])
    db.seed("predictions_bonus", [
        {"user_id": user_id, "question_id": 1, "chosen_option": "USA"},
    ])


def _score_row(db, user_id: str) -> dict:
    return next(r for r in db.rows("scores") if r["user_id"] == user_id)


def test_full_perfect_scores_breakdown(fake_db):
    _seed_full_tournament(fake_db)
    recalculate_all_scores()

    row = _score_row(fake_db, U1)
    assert row["group_stage_pts"] == 8       # 2*(qualifier+exact) + 2*exact + 2 advancer
    assert row["bracket_pts"] == 12          # R32(1) + QF(3) + Final(8)
    assert row["champion_pts"] == 16         # champion 13 + dark horse 3
    assert row["golden_boot_pts"] == 7
    assert row["bonus_pts"] == 2
    assert row["total_pts"] == 45
    assert row["total_pts"] == (
        row["group_stage_pts"] + row["bracket_pts"] + row["champion_pts"]
        + row["golden_boot_pts"] + row["bonus_pts"]
    )


def test_user_without_predictions_scores_zero(fake_db):
    _seed_full_tournament(fake_db)
    recalculate_all_scores()

    row = _score_row(fake_db, U2)
    assert row["total_pts"] == 0
    assert all(row[c] == 0 for c in (
        "group_stage_pts", "bracket_pts", "champion_pts", "golden_boot_pts", "bonus_pts"))


def test_every_profile_gets_a_score_row(fake_db):
    _seed_full_tournament(fake_db)
    recalculate_all_scores()
    scored_ids = {r["user_id"] for r in fake_db.rows("scores")}
    assert scored_ids == {U1, U2}


def test_recalc_is_idempotent_and_upserts(fake_db):
    _seed_full_tournament(fake_db)
    recalculate_all_scores()
    first = _score_row(fake_db, U1)["total_pts"]
    recalculate_all_scores()

    # Same total, and no duplicate rows (upsert on user_id).
    assert _score_row(fake_db, U1)["total_pts"] == first
    assert len(fake_db.rows("scores")) == 2


def test_partial_data_group_only(fake_db):
    """Only group results exist -> only group pts contribute, no errors."""
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("results_group_stage", [
        {"group_letter": "A", "final_ranking": ["A1", "A2", "A3", "A4"],
         "third_place_advances": False},
    ])
    fake_db.seed("predictions_group_stage", [
        {"user_id": U1, "group_letter": "A",
         "predicted_ranking": ["A1", "A2", "A3", "A4"], "third_place_advances": False},
    ])
    recalculate_all_scores()

    row = _score_row(fake_db, U1)
    assert row["group_stage_pts"] == 6     # exact all 4 + both top-2 qualifiers, no advancer
    assert row["bracket_pts"] == 0
    assert row["champion_pts"] == 0
    assert row["total_pts"] == 6


def test_incremental_round_addition_updates_total(fake_db):
    """Adding a later round's winner increases the total on the next recalc."""
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    fake_db.seed("real_bracket", [
        {"id": 101, "round": "R32", "slot": 1, "team_a": "X", "team_b": "Y",
         "winner": "X", "is_penalty": False},
        {"id": 201, "round": "R16", "slot": 1, "team_a": "X", "team_b": "W",
         "winner": None, "is_penalty": False},   # not played yet
    ])
    fake_db.seed("predictions_bracket", [
        {"user_id": U1, "matchup_id": 101, "predicted_winner": "X"},
        {"user_id": U1, "matchup_id": 201, "predicted_winner": "X"},
    ])
    recalculate_all_scores()
    assert _score_row(fake_db, U1)["bracket_pts"] == 1   # only R32 decided

    # Admin records the R16 winner; recompute.
    fake_db.table("real_bracket").update({"winner": "X"}).eq("id", 201).execute()
    recalculate_all_scores()
    assert _score_row(fake_db, U1)["bracket_pts"] == 3   # R32(1) + R16(2)


def test_no_profiles_is_noop(fake_db):
    recalculate_all_scores()
    assert fake_db.rows("scores") == []


def test_corrupt_group_should_not_wipe_bracket_points(fake_db):
    """Spec: absent/edge data in one category must not erase others (partial-data resilience).

    Regression guard for BUG-1 (fixed): scoring is now resilient per-category, so a corrupt
    group row contributes 0 without zeroing the user's valid bracket pick.
    """
    fake_db.seed("profiles", [{"id": U1, "email": "a@t.com", "display_name": "A"}])
    # Valid, scorable bracket pick.
    fake_db.seed("real_bracket", [
        {"id": 101, "round": "R32", "slot": 1, "team_a": "X", "team_b": "Y",
         "winner": "X", "is_penalty": False},
    ])
    fake_db.seed("predictions_bracket", [
        {"user_id": U1, "matchup_id": 101, "predicted_winner": "X"},
    ])
    # Corrupt group prediction (only 3 teams) — triggers IndexError deep in scoring.
    fake_db.seed("results_group_stage", [
        {"group_letter": "A", "final_ranking": ["A1", "A2", "A3", "A4"],
         "third_place_advances": False},
    ])
    fake_db.seed("predictions_group_stage", [
        {"user_id": U1, "group_letter": "A",
         "predicted_ranking": ["A1", "A2", "A3"], "third_place_advances": False},
    ])
    recalculate_all_scores()

    # The bracket pick is valid and should still score regardless of the bad group row.
    assert _score_row(fake_db, U1)["bracket_pts"] == 1