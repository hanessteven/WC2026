"""
Unit tests for src/scoring.py — pure functions, no DB required.

Covers:
- Each per-category scorer in isolation
- Partial tournament data (missing results → 0, not errors)
- Incremental round additions update totals correctly
- Idempotency (same inputs → same output)
- Tie scenarios (bonus question, golden boot)
- Full ScoringBreakdown totals match scoring_rules.md values
"""
import pytest
from uuid import uuid4

from src.models import (
    BonusAnswer,
    ChampionPick,
    GoldenBootSelection,
    GroupStagePrediction,
    GroupStageResult,
    PlayerGoals,
    RealMatchup,
    Round,
    RoundPick,
    TournamentResults,
    UserPredictions,
    CHAMPION_PTS,
    DARK_HORSE_PTS,
    GOLDEN_BOOT_WINNER_PTS,
    BONUS_QUESTION_PTS,
)
from src.scoring import (
    calculate_scores,
    score_bonus,
    score_bracket,
    score_champion,
    score_golden_boot,
    score_group,
    score_group_stage,
)

UID = uuid4()


# ── Test helpers ───────────────────────────────────────────────────────────────

def _gp(letter: str, ranking: list[str], tp: bool = False) -> GroupStagePrediction:
    return GroupStagePrediction.model_construct(
        group_letter=letter, predicted_ranking=ranking, third_place_advances=tp
    )


def _gr(letter: str, ranking: list[str], tp: bool = False) -> GroupStageResult:
    return GroupStageResult(
        group_letter=letter, final_ranking=ranking, third_place_advances=tp
    )


def _matchup(
    mid: int,
    round_: Round,
    team_a: str,
    team_b: str,
    winner: str | None = None,
) -> RealMatchup:
    return RealMatchup(
        id=mid, round=round_, slot=mid,
        team_a=team_a, team_b=team_b, winner=winner,
    )


def _pick(matchup_id: int, winner: str) -> RoundPick:
    return RoundPick(matchup_id=matchup_id, predicted_winner=winner)


def _preds(**kwargs) -> UserPredictions:
    defaults = dict(
        user_id=UID,
        group_stage=[],
        champion_pick=None,
        bracket_picks=[],
        golden_boot=[],
        bonus_answers=[],
    )
    defaults.update(kwargs)
    return UserPredictions.model_construct(**defaults)


# ── score_group ────────────────────────────────────────────────────────────────

class TestScoreGroup:
    def test_all_exact(self):
        # Perfect group: all 4 positions correct
        # Pos 0: qualifier(1) + exact(1) = 2
        # Pos 1: qualifier(1) + exact(1) = 2
        # Pos 2: exact(1) = 1
        # Pos 3: exact(1) = 1
        pred = _gp("A", ["Fr", "En", "Br", "Ge"])
        result = _gr("A", ["Fr", "En", "Br", "Ge"])
        assert score_group(pred, result) == 6

    def test_all_exact_with_tp_advancer(self):
        pred = _gp("A", ["Fr", "En", "Br", "Ge"], tp=True)
        result = _gr("A", ["Fr", "En", "Br", "Ge"], tp=True)
        assert score_group(pred, result) == 8  # 6 + 2

    def test_top2_swapped(self):
        # Both teams in top 2 but wrong position
        pred = _gp("A", ["En", "Fr", "Br", "Ge"])
        result = _gr("A", ["Fr", "En", "Br", "Ge"])
        # En: qualifier(1), wrong exact → 1
        # Fr: qualifier(1), wrong exact → 1
        # Br: exact(1) → 1
        # Ge: exact(1) → 1
        assert score_group(pred, result) == 4

    def test_one_correct_qualifier_wrong_position(self):
        pred = _gp("A", ["Fr", "Br", "En", "Ge"])
        result = _gr("A", ["Fr", "En", "Br", "Ge"])
        # Fr: qualifier(1) + exact(1) = 2
        # Br: NOT in top2 of result, wrong exact → 0
        # En: exact? No (pred pos2=En, result pos2=Br). En not in pred top2. → 0
        # Ge: exact(1) → 1
        assert score_group(pred, result) == 3

    def test_completely_wrong(self):
        pred = _gp("A", ["Ge", "Br", "Fr", "En"])
        result = _gr("A", ["Fr", "En", "Br", "Ge"])
        # Ge: not top2 result, wrong exact → 0
        # Br: not top2 result (Br is 3rd), wrong exact → 0
        # Fr: not in pred top2, but pred pos2=Fr, result pos2=Br → wrong exact → 0
        # En: not in pred top2, wrong exact → 0
        assert score_group(pred, result) == 0

    def test_tp_advancer_miss(self):
        pred = _gp("A", ["Fr", "En", "Br", "Ge"], tp=True)
        result = _gr("A", ["Fr", "En", "Br", "Ge"], tp=False)
        assert score_group(pred, result) == 6  # no tp bonus

    def test_tp_advancer_not_predicted(self):
        pred = _gp("A", ["Fr", "En", "Br", "Ge"], tp=False)
        result = _gr("A", ["Fr", "En", "Br", "Ge"], tp=True)
        assert score_group(pred, result) == 6  # didn't predict → no bonus

    def test_max_points_per_group(self):
        # 2+2+1+1+2 = 8 maximum
        pred = _gp("A", ["Fr", "En", "Br", "Ge"], tp=True)
        result = _gr("A", ["Fr", "En", "Br", "Ge"], tp=True)
        assert score_group(pred, result) == 8


# ── score_group_stage ─────────────────────────────────────────────────────────

class TestScoreGroupStage:
    def test_empty(self):
        assert score_group_stage([], []) == 0

    def test_no_results(self):
        assert score_group_stage([_gp("A", ["X", "Y", "Z", "W"])], []) == 0

    def test_partial_results(self):
        # Only group A result available — group B not scored
        preds = [_gp("A", ["X", "Y", "Z", "W"]), _gp("B", ["P", "Q", "R", "S"])]
        results = [_gr("A", ["X", "Y", "Z", "W"])]
        assert score_group_stage(preds, results) == 6

    def test_multiple_groups(self):
        preds = [
            _gp("A", ["Fr", "En", "Br", "Ge"]),
            _gp("B", ["Sp", "Ar", "Po", "Ne"]),
        ]
        results = [
            _gr("A", ["Fr", "En", "Br", "Ge"]),
            _gr("B", ["Sp", "Ar", "Po", "Ne"]),
        ]
        assert score_group_stage(preds, results) == 12  # 6 each


# ── score_bracket ─────────────────────────────────────────────────────────────

class TestScoreBracket:
    def test_empty(self):
        assert score_bracket([], []) == 0

    def test_no_results(self):
        matchups = [_matchup(1, Round.R32, "Fr", "En")]  # winner=None
        assert score_bracket([_pick(1, "Fr")], matchups) == 0

    def test_correct_r32(self):
        matchups = [_matchup(1, Round.R32, "Fr", "En", "Fr")]
        assert score_bracket([_pick(1, "Fr")], matchups) == 1

    def test_wrong_r32(self):
        matchups = [_matchup(1, Round.R32, "Fr", "En", "En")]
        assert score_bracket([_pick(1, "Fr")], matchups) == 0

    def test_fibonacci_weights(self):
        matchups = [
            _matchup(1, Round.R32, "A", "B", "A"),
            _matchup(2, Round.R16, "C", "D", "C"),
            _matchup(3, Round.QF,  "E", "F", "E"),
            _matchup(4, Round.SF,  "G", "H", "G"),
            _matchup(5, Round.F,   "I", "J", "I"),
        ]
        picks = [_pick(m.id, m.team_a) for m in matchups]
        assert score_bracket(picks, matchups) == 19  # 1+2+3+5+8

    def test_partial_rounds(self):
        # R32 result in, R16 not yet
        matchups = [
            _matchup(1, Round.R32, "Fr", "En", "Fr"),
            _matchup(2, Round.R16, "Br", "Ge"),       # no winner
        ]
        picks = [_pick(1, "Fr"), _pick(2, "Br")]
        assert score_bracket(picks, matchups) == 1

    def test_no_pick_for_match(self):
        matchups = [_matchup(1, Round.R32, "Fr", "En", "Fr")]
        assert score_bracket([], matchups) == 0

    def test_incremental_additions(self):
        preds = [_pick(1, "Fr"), _pick(2, "Br")]
        results_r32 = [_matchup(1, Round.R32, "Fr", "En", "Fr")]
        results_r32_r16 = [
            _matchup(1, Round.R32, "Fr", "En", "Fr"),
            _matchup(2, Round.R16, "Br", "Ge", "Br"),
        ]
        assert score_bracket(preds, results_r32) == 1
        assert score_bracket(preds, results_r32_r16) == 3  # 1 + 2


# ── score_champion ────────────────────────────────────────────────────────────

class TestScoreChampion:
    def test_no_pick(self):
        assert score_champion(None, []) == 0

    def test_correct_champion(self):
        knockout = [_matchup(99, Round.F, "Fr", "Br", "Fr")]
        pick = ChampionPick(champion="Fr")
        assert score_champion(pick, knockout) == CHAMPION_PTS  # 13

    def test_wrong_champion(self):
        knockout = [_matchup(99, Round.F, "Fr", "Br", "Br")]
        pick = ChampionPick(champion="Fr")
        assert score_champion(pick, knockout) == 0

    def test_no_final_result(self):
        knockout = [_matchup(99, Round.F, "Fr", "Br")]  # winner=None
        pick = ChampionPick(champion="Fr")
        assert score_champion(pick, knockout) == 0

    def test_dark_horse_at_qf(self):
        knockout = [_matchup(10, Round.QF, "Mo", "Fr")]
        pick = ChampionPick(champion="Fr", dark_horse="Mo")
        assert score_champion(pick, knockout) == DARK_HORSE_PTS  # 3

    def test_dark_horse_not_at_qf(self):
        knockout = [_matchup(10, Round.QF, "Br", "Fr")]
        pick = ChampionPick(champion="Fr", dark_horse="Mo")
        assert score_champion(pick, knockout) == 0

    def test_dark_horse_qf_detection_uses_both_teams(self):
        # Dark horse is team_b in a QF matchup
        knockout = [_matchup(10, Round.QF, "Fr", "Mo")]
        pick = ChampionPick(champion="Fr", dark_horse="Mo")
        assert score_champion(pick, knockout) == DARK_HORSE_PTS

    def test_champion_and_dark_horse_both_correct(self):
        knockout = [
            _matchup(10, Round.QF, "Mo", "Fr"),
            _matchup(99, Round.F,  "Fr", "Br", "Fr"),
        ]
        pick = ChampionPick(champion="Fr", dark_horse="Mo")
        assert score_champion(pick, knockout) == CHAMPION_PTS + DARK_HORSE_PTS  # 16

    def test_dark_horse_in_sf_not_qf_rows(self):
        # SF matchup but no QF rows entered yet — dark horse not awarded
        knockout = [_matchup(20, Round.SF, "Mo", "Fr")]
        pick = ChampionPick(champion="Fr", dark_horse="Mo")
        assert score_champion(pick, knockout) == 0

    def test_no_dark_horse_pick(self):
        knockout = [_matchup(10, Round.QF, "Mo", "Fr")]
        pick = ChampionPick(champion="Fr")  # no dark horse
        assert score_champion(pick, knockout) == 0


# ── score_golden_boot ─────────────────────────────────────────────────────────

class TestScoreGoldenBoot:
    def test_empty(self):
        assert score_golden_boot([], []) == 0

    def test_no_goals_data(self):
        picks = [GoldenBootSelection(player_id=1, player_name="Kane", cost=55)]
        assert score_golden_boot(picks, []) == 0

    def test_all_zero_goals(self):
        picks = [GoldenBootSelection(player_id=1, player_name="Kane", cost=55)]
        goals = [PlayerGoals(player_id=1, player_name="Kane", goals_scored=0)]
        assert score_golden_boot(picks, goals) == 0

    def test_drafted_top_scorer(self):
        picks = [GoldenBootSelection(player_id=1, player_name="Kane", cost=55)]
        goals = [
            PlayerGoals(player_id=1, player_name="Kane", goals_scored=8),
            PlayerGoals(player_id=2, player_name="Mbappe", goals_scored=5),
        ]
        assert score_golden_boot(picks, goals) == GOLDEN_BOOT_WINNER_PTS  # 7

    def test_not_top_scorer(self):
        picks = [GoldenBootSelection(player_id=2, player_name="Mbappe", cost=65)]
        goals = [
            PlayerGoals(player_id=1, player_name="Kane", goals_scored=8),
            PlayerGoals(player_id=2, player_name="Mbappe", goals_scored=5),
        ]
        assert score_golden_boot(picks, goals) == 0

    def test_tie_drafted_one_of_the_joint_top(self):
        # Both Kane and Mbappe on 8 — user drafted Kane → wins
        picks = [GoldenBootSelection(player_id=1, player_name="Kane", cost=55)]
        goals = [
            PlayerGoals(player_id=1, player_name="Kane", goals_scored=8),
            PlayerGoals(player_id=2, player_name="Mbappe", goals_scored=8),
        ]
        assert score_golden_boot(picks, goals) == GOLDEN_BOOT_WINNER_PTS

    def test_tie_drafted_neither_top(self):
        picks = [GoldenBootSelection(player_id=3, player_name="Haaland", cost=50)]
        goals = [
            PlayerGoals(player_id=1, player_name="Kane", goals_scored=8),
            PlayerGoals(player_id=2, player_name="Mbappe", goals_scored=8),
            PlayerGoals(player_id=3, player_name="Haaland", goals_scored=6),
        ]
        assert score_golden_boot(picks, goals) == 0

    def test_multiple_drafted_one_is_top(self):
        picks = [
            GoldenBootSelection(player_id=1, player_name="Kane", cost=55),
            GoldenBootSelection(player_id=3, player_name="Haaland", cost=50),
        ]
        goals = [
            PlayerGoals(player_id=1, player_name="Kane", goals_scored=8),
            PlayerGoals(player_id=3, player_name="Haaland", goals_scored=6),
        ]
        assert score_golden_boot(picks, goals) == GOLDEN_BOOT_WINNER_PTS


# ── score_bonus ───────────────────────────────────────────────────────────────

class TestScoreBonus:
    def _answer(self, qid: int, option: str) -> BonusAnswer:
        return BonusAnswer.model_construct(
            question_id=qid, chosen_option=option, valid_options=[]
        )

    def test_empty(self):
        assert score_bonus([], {}) == 0

    def test_no_correct_options_set(self):
        answers = [self._answer(1, "USA")]
        assert score_bonus(answers, {}) == 0

    def test_correct_single_option(self):
        answers = [self._answer(1, "USA")]
        assert score_bonus(answers, {1: ["USA"]}) == BONUS_QUESTION_PTS  # 2

    def test_wrong_answer(self):
        answers = [self._answer(1, "Mexico")]
        assert score_bonus(answers, {1: ["USA"]}) == 0

    def test_tie_pick_first_correct_option(self):
        answers = [self._answer(1, "USA")]
        assert score_bonus(answers, {1: ["USA", "Mexico"]}) == BONUS_QUESTION_PTS

    def test_tie_pick_second_correct_option(self):
        answers = [self._answer(1, "Mexico")]
        assert score_bonus(answers, {1: ["USA", "Mexico"]}) == BONUS_QUESTION_PTS

    def test_multiple_questions_partial_correct(self):
        answers = [
            self._answer(1, "USA"),       # correct
            self._answer(2, "CONMEBOL"),  # wrong
            self._answer(3, "Yes"),       # correct
        ]
        bonus_correct = {1: ["USA"], 2: ["UEFA"], 3: ["Yes"]}
        assert score_bonus(answers, bonus_correct) == 4  # 2 + 0 + 2

    def test_question_result_not_entered_yet(self):
        # Q2 has no correct_options — only Q1 scored
        answers = [self._answer(1, "USA"), self._answer(2, "CONMEBOL")]
        bonus_correct = {1: ["USA"]}
        assert score_bonus(answers, bonus_correct) == BONUS_QUESTION_PTS

    def test_no_answer_for_question(self):
        # correct_options set for Q1 but user never answered it
        assert score_bonus([], {1: ["USA"]}) == 0


# ── calculate_scores ──────────────────────────────────────────────────────────

class TestCalculateScores:
    def test_all_empty(self):
        sb = calculate_scores(_preds(), TournamentResults())
        assert sb.total_pts == 0
        assert sb.user_id == UID

    def test_total_matches_category_sum(self):
        preds = _preds(
            group_stage=[_gp("A", ["Fr", "En", "Br", "Ge"])],
            champion_pick=ChampionPick(champion="Fr"),
        )
        results = TournamentResults(
            group_stage=[_gr("A", ["Fr", "En", "Br", "Ge"])],
            knockout=[_matchup(99, Round.F, "Fr", "Br", "Fr")],
        )
        sb = calculate_scores(preds, results)
        assert sb.total_pts == sb.group_stage_pts + sb.bracket_pts + sb.champion_pts + sb.golden_boot_pts + sb.bonus_pts

    def test_partial_tournament_group_only(self):
        preds = _preds(
            group_stage=[_gp("A", ["Fr", "En", "Br", "Ge"])],
            bracket_picks=[_pick(1, "Fr")],
        )
        results = TournamentResults(
            group_stage=[_gr("A", ["Fr", "En", "Br", "Ge"])],
            # no knockout results
        )
        sb = calculate_scores(preds, results)
        assert sb.group_stage_pts == 6
        assert sb.bracket_pts == 0

    def test_incremental_rounds_increase_total(self):
        preds = _preds(bracket_picks=[_pick(1, "Fr"), _pick(2, "Br")])

        sb_r32 = calculate_scores(preds, TournamentResults(
            knockout=[_matchup(1, Round.R32, "Fr", "En", "Fr")],
        ))
        sb_r32_r16 = calculate_scores(preds, TournamentResults(
            knockout=[
                _matchup(1, Round.R32, "Fr", "En", "Fr"),
                _matchup(2, Round.R16, "Br", "Ge", "Br"),
            ],
        ))
        assert sb_r32.bracket_pts == 1
        assert sb_r32_r16.bracket_pts == 3  # 1 + 2
        assert sb_r32_r16.total_pts > sb_r32.total_pts

    def test_idempotent(self):
        preds = _preds(
            group_stage=[_gp("A", ["Fr", "En", "Br", "Ge"])],
            bracket_picks=[_pick(1, "Fr")],
            champion_pick=ChampionPick(champion="Br", dark_horse="Fr"),
        )
        results = TournamentResults(
            group_stage=[_gr("A", ["Fr", "En", "Br", "Ge"])],
            knockout=[
                _matchup(1,  Round.R32, "Fr", "En", "Fr"),
                _matchup(10, Round.QF,  "Fr", "Sp"),
                _matchup(99, Round.F,   "Br", "Fr", "Br"),
            ],
        )
        sb1 = calculate_scores(preds, results)
        sb2 = calculate_scores(preds, results)
        assert sb1.total_pts == sb2.total_pts
        assert sb1.group_stage_pts == sb2.group_stage_pts
        assert sb1.bracket_pts == sb2.bracket_pts
        assert sb1.champion_pts == sb2.champion_pts

    def test_full_perfect_score_components(self):
        # Verify that each category fires correctly in a full scenario
        preds = _preds(
            group_stage=[_gp("A", ["Fr", "En", "Br", "Ge"], tp=True)],
            champion_pick=ChampionPick(champion="Fr", dark_horse="Mo"),
            bracket_picks=[
                _pick(1, "Fr"),   # R32 correct
                _pick(99, "Fr"),  # Final correct
            ],
            golden_boot=[GoldenBootSelection(player_id=7, player_name="Mbappe", cost=65)],
            bonus_answers=[
                BonusAnswer.model_construct(question_id=1, chosen_option="USA", valid_options=[])
            ],
        )
        results = TournamentResults(
            group_stage=[_gr("A", ["Fr", "En", "Br", "Ge"], tp=True)],
            knockout=[
                _matchup(1,  Round.R32, "Fr", "En", "Fr"),
                _matchup(10, Round.QF,  "Mo", "Sp"),
                _matchup(99, Round.F,   "Fr", "Br", "Fr"),
            ],
            player_goals=[
                PlayerGoals(player_id=7, player_name="Mbappe", goals_scored=9),
                PlayerGoals(player_id=8, player_name="Kane",   goals_scored=6),
            ],
            bonus_correct={1: ["USA"]},
        )
        sb = calculate_scores(preds, results)
        assert sb.group_stage_pts == 8   # all exact + tp
        assert sb.bracket_pts == 1 + 8  # R32(1) + Final(8)
        assert sb.champion_pts == CHAMPION_PTS + DARK_HORSE_PTS  # 13 + 3
        assert sb.golden_boot_pts == GOLDEN_BOOT_WINNER_PTS      # 7
        assert sb.bonus_pts == BONUS_QUESTION_PTS                 # 2
        assert sb.total_pts == 8 + 9 + 16 + 7 + 2  # 42