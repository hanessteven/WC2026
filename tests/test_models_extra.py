"""Extra model coverage beyond test_models.py — construction + enum + defaults."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models import (
    BonusAnswer,
    ChampionPick,
    GroupStageResult,
    PlayerGoals,
    RealMatchup,
    Round,
    RoundPick,
    ScoringBreakdown,
    TournamentResults,
    UserPredictions,
)

USER_ID = uuid4()


def test_round_enum_values():
    assert [r.value for r in Round] == ["R32", "R16", "QF", "SF", "F"]
    assert Round("QF") is Round.QF


def test_realmatchup_defaults():
    m = RealMatchup(id=1, round=Round.R32, slot=1, team_a="A", team_b="B")
    assert m.winner is None
    assert m.is_penalty is False


def test_roundpick_basic():
    p = RoundPick(matchup_id=5, predicted_winner="Brazil")
    assert p.matchup_id == 5 and p.predicted_winner == "Brazil"


def test_champion_pick_dark_horse_optional():
    assert ChampionPick(champion="Brazil").dark_horse is None
    assert ChampionPick(champion="Brazil", dark_horse="Japan").dark_horse == "Japan"


def test_champion_pick_rejects_dark_horse_equal_to_champion():
    with pytest.raises(ValidationError, match="different team"):
        ChampionPick(champion="Brazil", dark_horse="Brazil")


def test_bonus_answer_tie_option_list_allows_any_member():
    a = BonusAnswer(question_id=1, chosen_option="Mexico",
                    valid_options=["USA", "Mexico", "Canada"])
    assert a.chosen_option == "Mexico"


def test_group_result_and_player_goals_construct():
    gr = GroupStageResult(group_letter="A", final_ranking=["a", "b", "c", "d"])
    assert gr.third_place_advances is False
    pg = PlayerGoals(player_id=1, player_name="Striker", goals_scored=4)
    assert pg.goals_scored == 4


def test_tournament_results_defaults_empty():
    tr = TournamentResults()
    assert tr.group_stage == [] and tr.knockout == []
    assert tr.player_goals == [] and tr.bonus_correct == {}


def test_user_predictions_defaults_empty():
    up = UserPredictions(user_id=USER_ID)
    assert up.group_stage == [] and up.bracket_picks == []
    assert up.champion_pick is None


def test_scoring_breakdown_zero_default_is_consistent():
    sb = ScoringBreakdown(user_id=USER_ID)
    assert sb.total_pts == 0


def test_scoring_breakdown_partial_categories_must_sum():
    with pytest.raises(ValidationError, match="does not match category sum"):
        ScoringBreakdown(user_id=USER_ID, group_stage_pts=5, total_pts=4)