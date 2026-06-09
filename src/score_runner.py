"""
Score runner — DB orchestration for the scoring engine.

Fetches predictions and results from Supabase, calls calculate_scores(),
and writes ScoringBreakdown rows into the scores table.

No st.* imports — safe to call from any context (admin saves, CLI, tests).
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

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
)
from src.db import get_admin_client
from src.scoring import calculate_scores


def _build_tournament_results(client) -> TournamentResults:
    """Load all admin-entered results from the DB into a TournamentResults object."""

    # Group stage
    gs_rows = (
        client.table("results_group_stage")
        .select("group_letter, final_ranking, third_place_advances")
        .execute()
        .data
    )
    group_stage = [
        GroupStageResult(
            group_letter=r["group_letter"],
            final_ranking=r["final_ranking"],
            third_place_advances=r["third_place_advances"],
        )
        for r in gs_rows
    ]

    # All knockout matchups (winner may be None — needed for dark-horse QF check)
    bracket_rows = (
        client.table("real_bracket")
        .select("id, round, slot, team_a, team_b, winner, is_penalty")
        .order("round")
        .order("slot")
        .execute()
        .data
    )
    knockout = [
        RealMatchup(
            id=r["id"],
            round=Round(r["round"]),
            slot=r["slot"],
            team_a=r["team_a"],
            team_b=r["team_b"],
            winner=r.get("winner"),
            is_penalty=r.get("is_penalty", False),
        )
        for r in bracket_rows
    ]

    # Player goals — fetch names in a second query to avoid join complexity
    goals_rows = (
        client.table("results_player_goals")
        .select("player_id, goals_scored")
        .execute()
        .data
    )
    player_goals: list[PlayerGoals] = []
    if goals_rows:
        pids = [r["player_id"] for r in goals_rows]
        name_rows = (
            client.table("seed_players")
            .select("id, name")
            .in_("id", pids)
            .execute()
            .data
        )
        name_map = {r["id"]: r["name"] for r in name_rows}
        player_goals = [
            PlayerGoals(
                player_id=r["player_id"],
                player_name=name_map.get(r["player_id"], ""),
                goals_scored=r["goals_scored"],
            )
            for r in goals_rows
        ]

    # Bonus correct options
    bonus_rows = (
        client.table("bonus_question_defs")
        .select("id, correct_options")
        .execute()
        .data
    )
    bonus_correct = {
        r["id"]: r["correct_options"]
        for r in bonus_rows
        if r.get("correct_options")
    }

    return TournamentResults(
        group_stage=group_stage,
        knockout=knockout,
        player_goals=player_goals,
        bonus_correct=bonus_correct,
    )


def _build_user_predictions(user_id: str, client) -> UserPredictions:
    """
    Load one user's predictions from the DB into a UserPredictions object.

    Uses model_construct() to bypass Pydantic validators — data is already
    validated at save time and we need scoring to be robust on edge cases.
    """

    # Group stage
    gs_rows = (
        client.table("predictions_group_stage")
        .select("group_letter, predicted_ranking, third_place_advances")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    group_stage = [
        GroupStagePrediction.model_construct(
            group_letter=r["group_letter"],
            predicted_ranking=r["predicted_ranking"],
            third_place_advances=r["third_place_advances"],
        )
        for r in gs_rows
    ]

    # Champion pick
    cp_rows = (
        client.table("predictions_champion")
        .select("champion, dark_horse")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    champion_pick = (
        ChampionPick.model_construct(
            champion=cp_rows[0]["champion"],
            dark_horse=cp_rows[0].get("dark_horse"),
        )
        if cp_rows else None
    )

    # Bracket picks
    bp_rows = (
        client.table("predictions_bracket")
        .select("matchup_id, predicted_winner")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    bracket_picks = [
        RoundPick.model_construct(
            matchup_id=r["matchup_id"],
            predicted_winner=r["predicted_winner"],
        )
        for r in bp_rows
    ]

    # Golden boot — fetch costs in a second query
    gb_rows = (
        client.table("predictions_golden_boot")
        .select("player_id")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    golden_boot: list[GoldenBootSelection] = []
    if gb_rows:
        pids = [r["player_id"] for r in gb_rows]
        pdata = (
            client.table("seed_players")
            .select("id, name, cost")
            .in_("id", pids)
            .execute()
            .data
        )
        pmap = {r["id"]: r for r in pdata}
        golden_boot = [
            GoldenBootSelection.model_construct(
                player_id=r["player_id"],
                player_name=pmap[r["player_id"]]["name"],
                cost=pmap[r["player_id"]]["cost"],
            )
            for r in gb_rows
            if r["player_id"] in pmap
        ]

    # Bonus answers — bypass the valid_options validator (data already validated at save)
    ba_rows = (
        client.table("predictions_bonus")
        .select("question_id, chosen_option")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    bonus_answers = [
        BonusAnswer.model_construct(
            question_id=r["question_id"],
            chosen_option=r["chosen_option"],
            valid_options=[],
        )
        for r in ba_rows
    ]

    return UserPredictions.model_construct(
        user_id=UUID(user_id),
        group_stage=group_stage,
        champion_pick=champion_pick,
        bracket_picks=bracket_picks,
        golden_boot=golden_boot,
        bonus_answers=bonus_answers,
    )


def _score_row_for_user(user_id: str, client, tournament_results, now: str) -> dict:
    """Build one user's scores-table row. Falls back to zeros only if the user's
    predictions can't be loaded at all (e.g. a malformed id) — per-category
    resilience lives in calculate_scores, so a single bad category never zeroes
    the rest."""
    try:
        predictions = _build_user_predictions(user_id, client)
        breakdown = calculate_scores(predictions, tournament_results)
        return {
            "user_id": user_id,
            "group_stage_pts": breakdown.group_stage_pts,
            "bracket_pts": breakdown.bracket_pts,
            "champion_pts": breakdown.champion_pts,
            "golden_boot_pts": breakdown.golden_boot_pts,
            "bonus_pts": breakdown.bonus_pts,
            "total_pts": breakdown.total_pts,
            "calculated_at": now,
        }
    except Exception:
        return {
            "user_id": user_id,
            "group_stage_pts": 0,
            "bracket_pts": 0,
            "champion_pts": 0,
            "golden_boot_pts": 0,
            "bonus_pts": 0,
            "total_pts": 0,
            "calculated_at": now,
        }


def recalculate_all_scores() -> None:
    """
    Recompute scores for every registered user and upsert into the scores table.

    Called automatically after any admin result save. Idempotent — safe to call
    repeatedly; each run overwrites the previous score row per user.
    """
    client = get_admin_client()
    users = client.table("profiles").select("id").execute().data
    if not users:
        return

    tournament_results = _build_tournament_results(client)
    now = datetime.now(timezone.utc).isoformat()
    score_rows = [
        _score_row_for_user(u["id"], client, tournament_results, now) for u in users
    ]

    client.table("scores").upsert(score_rows, on_conflict="user_id").execute()


def recalculate_user_score(user_id: str) -> None:
    """
    Recompute and upsert a single user's score.

    Cheap enough to call after each user prediction save, which keeps a user's
    standing fresh even if they edit a prediction after some results already
    exist (rather than waiting for the next admin result entry).
    """
    client = get_admin_client()
    tournament_results = _build_tournament_results(client)
    now = datetime.now(timezone.utc).isoformat()
    row = _score_row_for_user(user_id, client, tournament_results, now)

    client.table("scores").upsert([row], on_conflict="user_id").execute()