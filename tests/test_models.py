"""Unit tests for src/models.py validators."""
import pytest
from uuid import uuid4
from pydantic import ValidationError

from src.models import (
    GroupStagePrediction,
    ChampionPick,
    BonusAnswer,
    GoldenBootSelection,
    UserPredictions,
    ScoringBreakdown,
    GOLDEN_BOOT_BUDGET,
)

USER_ID = uuid4()
GROUPS = "ABCDEFGHIJKL"


# ── GroupStagePrediction ──────────────────────────────────────────────────────

def test_group_ranking_valid():
    g = GroupStagePrediction(
        group_letter="A",
        predicted_ranking=["USA", "Mexico", "Canada", "Brazil"],
        third_place_advances=True,
    )
    assert g.predicted_ranking[0] == "USA"


def test_group_ranking_too_short():
    with pytest.raises(ValidationError, match="exactly 4 teams"):
        GroupStagePrediction(
            group_letter="A",
            predicted_ranking=["USA", "Mexico", "Canada"],
        )


def test_group_ranking_too_long():
    with pytest.raises(ValidationError, match="exactly 4 teams"):
        GroupStagePrediction(
            group_letter="A",
            predicted_ranking=["USA", "Mexico", "Canada", "Brazil", "Argentina"],
        )


def test_group_ranking_duplicates():
    with pytest.raises(ValidationError, match="duplicate"):
        GroupStagePrediction(
            group_letter="A",
            predicted_ranking=["USA", "USA", "Canada", "Brazil"],
        )


# ── BonusAnswer ───────────────────────────────────────────────────────────────

def test_bonus_answer_valid():
    a = BonusAnswer(
        question_id=1,
        chosen_option="USA",
        valid_options=["USA", "Mexico", "Canada", "Tie"],
    )
    assert a.chosen_option == "USA"


def test_bonus_answer_invalid_option():
    with pytest.raises(ValidationError, match="not a valid option"):
        BonusAnswer(
            question_id=1,
            chosen_option="Argentina",
            valid_options=["USA", "Mexico", "Canada", "Tie"],
        )


# ── UserPredictions — third-place count ──────────────────────────────────────

def _make_group_predictions(advancing_letters: set[str]) -> list[GroupStagePrediction]:
    """Build 12 GroupStagePredictions with third_place_advances set for the given group letters."""
    preds = []
    for letter in GROUPS:
        teams = [f"Team{letter}1", f"Team{letter}2", f"Team{letter}3", f"Team{letter}4"]
        preds.append(GroupStagePrediction(
            group_letter=letter,
            predicted_ranking=teams,
            third_place_advances=(letter in advancing_letters),
        ))
    return preds


def test_third_place_exactly_8_valid():
    advancing = set(GROUPS[:8])  # A-H
    up = UserPredictions(user_id=USER_ID, group_stage=_make_group_predictions(advancing))
    assert sum(1 for g in up.group_stage if g.third_place_advances) == 8


def test_third_place_too_few():
    advancing = set(GROUPS[:7])  # only 7
    with pytest.raises(ValidationError, match="Exactly 8"):
        UserPredictions(user_id=USER_ID, group_stage=_make_group_predictions(advancing))


def test_third_place_too_many():
    advancing = set(GROUPS[:9])  # 9
    with pytest.raises(ValidationError, match="Exactly 8"):
        UserPredictions(user_id=USER_ID, group_stage=_make_group_predictions(advancing))


def test_third_place_not_validated_when_partial():
    """Validation only fires when all 12 groups are submitted."""
    partial = _make_group_predictions(set())[:6]  # only 6 groups, 0 advancing
    up = UserPredictions(user_id=USER_ID, group_stage=partial)
    assert len(up.group_stage) == 6


# ── UserPredictions — golden boot budget ─────────────────────────────────────

def _make_players(costs: list[int]) -> list[GoldenBootSelection]:
    return [
        GoldenBootSelection(player_id=i, player_name=f"Player{i}", cost=c)
        for i, c in enumerate(costs)
    ]


def test_golden_boot_within_budget():
    up = UserPredictions(user_id=USER_ID, golden_boot=_make_players([30, 15, 10, 5]))
    assert sum(p.cost for p in up.golden_boot) == 60


def test_golden_boot_exactly_at_budget():
    costs = [GOLDEN_BOOT_BUDGET]
    up = UserPredictions(user_id=USER_ID, golden_boot=_make_players(costs))
    assert sum(p.cost for p in up.golden_boot) == GOLDEN_BOOT_BUDGET


def test_golden_boot_over_budget():
    with pytest.raises(ValidationError, match="exceeds budget"):
        UserPredictions(user_id=USER_ID, golden_boot=_make_players([60, 50]))


# ── ScoringBreakdown — total consistency ─────────────────────────────────────

def test_scoring_breakdown_valid():
    sb = ScoringBreakdown(
        user_id=USER_ID,
        group_stage_pts=10,
        bracket_pts=5,
        champion_pts=13,
        golden_boot_pts=3,
        bonus_pts=4,
        total_pts=35,
    )
    assert sb.total_pts == 35


def test_scoring_breakdown_total_mismatch():
    with pytest.raises(ValidationError, match="does not match category sum"):
        ScoringBreakdown(
            user_id=USER_ID,
            group_stage_pts=10,
            bracket_pts=5,
            champion_pts=0,
            golden_boot_pts=0,
            bonus_pts=0,
            total_pts=99,  # wrong
        )