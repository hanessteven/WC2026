"""
Scoring engine — pure Python, no st.* imports.

Accepts UserPredictions + TournamentResults, returns ScoringBreakdown.
Handles partial tournament data gracefully: absent results contribute 0.
Idempotent: identical inputs always produce identical output.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.models import (
    BONUS_QUESTION_PTS,
    CHAMPION_PTS,
    DARK_HORSE_PTS,
    GOLDEN_BOOT_WINNER_PTS,
    GROUP_EXACT_POS_PTS,
    GROUP_QUALIFIER_PTS,
    GROUP_THIRD_PLACE_PTS,
    BonusAnswer,
    ChampionPick,
    GoldenBootSelection,
    GroupStagePrediction,
    GroupStageResult,
    PlayerGoals,
    RealMatchup,
    Round,
    RoundPick,
    ScoringBreakdown,
    TournamentResults,
    UserPredictions,
)

# Points per correct winner, keyed by round.
ROUND_POINTS: dict[Round, int] = {
    Round.R32: 1,
    Round.R16: 2,
    Round.QF: 3,
    Round.SF: 5,
    Round.F: 8,
}


# ── Per-category scorers ───────────────────────────────────────────────────────

def score_group(
    pred: GroupStagePrediction,
    result: GroupStageResult,
) -> int:
    """Score one group. Up to 8 pts: qualifier + exact position + 3rd-place advancer."""
    pts = 0
    result_top2 = set(result.final_ranking[:2])

    for pos in range(4):
        pred_team = pred.predicted_ranking[pos]
        actual_team = result.final_ranking[pos]

        if pos < 2:
            # Qualifier pt: predicted team is in the real top 2 (any position)
            if pred_team in result_top2:
                pts += GROUP_QUALIFIER_PTS
            # Exact position bonus
            if pred_team == actual_team:
                pts += GROUP_EXACT_POS_PTS
        else:
            # 3rd/4th: only exact position — no qualifier bonus
            if pred_team == actual_team:
                pts += GROUP_EXACT_POS_PTS

    # Third-place advancer: 2 pts if user predicted this group's 3rd advances and they did
    if pred.third_place_advances and result.third_place_advances:
        pts += GROUP_THIRD_PLACE_PTS

    return pts


def score_group_stage(
    predictions: list[GroupStagePrediction],
    results: list[GroupStageResult],
) -> int:
    """Sum group scores across all groups that have results."""
    result_map = {r.group_letter: r for r in results}
    return sum(
        score_group(pred, result_map[pred.group_letter])
        for pred in predictions
        if pred.group_letter in result_map
    )


def score_bracket(
    picks: list[RoundPick],
    knockout: list[RealMatchup],
) -> int:
    """Score knockout bracket picks. Only matchups with a winner set contribute points."""
    result_map = {m.id: m for m in knockout if m.winner}
    pts = 0
    for pick in picks:
        matchup = result_map.get(pick.matchup_id)
        if matchup and pick.predicted_winner == matchup.winner:
            pts += ROUND_POINTS[matchup.round]
    return pts


def score_champion(
    pick: ChampionPick | None,
    knockout: list[RealMatchup],
) -> int:
    """
    Score the upfront champion + dark horse pick.

    Champion: 13 pts if the Final winner matches.
    Dark horse: 3 pts if the picked team appears in any QF matchup
                (team_a or team_b — regardless of whether that match has a result yet).
    """
    if not pick:
        return 0

    pts = 0

    # Champion: correct if they won the Final
    final = next(
        (m for m in knockout if m.round == Round.F and m.winner),
        None,
    )
    if final and pick.champion == final.winner:
        pts += CHAMPION_PTS

    # Dark horse: team must have reached (played in) QF
    if pick.dark_horse:
        qf_teams = {
            team
            for m in knockout
            if m.round == Round.QF
            for team in (m.team_a, m.team_b)
        }
        if pick.dark_horse in qf_teams:
            pts += DARK_HORSE_PTS

    return pts


def score_golden_boot(
    picks: list[GoldenBootSelection],
    player_goals: list[PlayerGoals],
) -> int:
    """
    7 pts if any drafted player is a joint or sole Golden Boot winner (top scorer).
    0 pts if all players scored 0 goals (tournament hasn't started or no data yet).
    """
    if not picks or not player_goals:
        return 0

    max_goals = max(p.goals_scored for p in player_goals)
    if max_goals == 0:
        return 0

    top_scorer_ids = {p.player_id for p in player_goals if p.goals_scored == max_goals}
    drafted_ids = {p.player_id for p in picks}

    return GOLDEN_BOOT_WINNER_PTS if drafted_ids & top_scorer_ids else 0


def score_bonus(
    answers: list[BonusAnswer],
    bonus_correct: dict[int, list[str]],
) -> int:
    """
    2 pts per correct bonus answer. Tie-aware: any option in correct_options counts.
    Questions with no correct_options set yet contribute 0.
    """
    answers_by_qid = {a.question_id: a.chosen_option for a in answers}
    pts = 0
    for qid, correct_options in bonus_correct.items():
        if not correct_options:
            continue
        user_answer = answers_by_qid.get(qid)
        if user_answer and user_answer in correct_options:
            pts += BONUS_QUESTION_PTS
    return pts


# ── Main entry point ───────────────────────────────────────────────────────────

def calculate_scores(
    predictions: UserPredictions,
    results: TournamentResults,
) -> ScoringBreakdown:
    """
    Compute a full ScoringBreakdown for one user.

    Safe on partial data: any category without results contributes 0.
    Idempotent: calling twice with the same inputs returns the same breakdown.
    """
    group_pts = score_group_stage(predictions.group_stage, results.group_stage)
    bracket_pts = score_bracket(predictions.bracket_picks, results.knockout)
    champion_pts = score_champion(predictions.champion_pick, results.knockout)
    golden_boot_pts = score_golden_boot(predictions.golden_boot, results.player_goals)
    bonus_pts = score_bonus(predictions.bonus_answers, results.bonus_correct)

    total = group_pts + bracket_pts + champion_pts + golden_boot_pts + bonus_pts

    return ScoringBreakdown(
        user_id=predictions.user_id,
        group_stage_pts=group_pts,
        bracket_pts=bracket_pts,
        champion_pts=champion_pts,
        golden_boot_pts=golden_boot_pts,
        bonus_pts=bonus_pts,
        total_pts=total,
        calculated_at=datetime.now(timezone.utc),
    )