"""Admin-only DB helpers — results, locks, bracket, user management.

All writes use the service-role client (bypasses RLS).
Never expose these functions to non-admin users.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.auth import get_current_user
from src.db import get_admin_client
from src.locks import load_lock_state, set_lock  # noqa: F401 — re-exported for page imports
from src.predictions import (
    load_bonus_questions,
    load_bracket_matchups,
    load_leaderboard,
)
from src.score_runner import recalculate_all_scores


# ── Results finalization (locking) ────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_group_result_locks() -> dict[str, bool]:
    """Return {group_letter: is_locked} for all 12 groups."""
    result = get_admin_client().table("results_group_lock").select("group_letter, is_locked").execute()
    return {row["group_letter"]: row["is_locked"] for row in result.data}


def set_group_result_lock(group_letter: str, locked: bool) -> None:
    """Lock or unlock a group's results. Invalidates the cache."""
    get_admin_client().table("results_group_lock").update(
        {"is_locked": locked}
    ).eq("group_letter", group_letter).execute()
    load_group_result_locks.clear()


@st.cache_data(ttl=30)
def load_golden_boot_result_lock() -> bool:
    """Return whether the golden boot results are locked."""
    result = get_admin_client().table("results_golden_boot_lock").select("is_locked").eq("id", 1).execute()
    return result.data[0]["is_locked"] if result.data else False


def set_golden_boot_result_lock(locked: bool) -> None:
    """Lock or unlock the golden boot results. Invalidates the cache."""
    get_admin_client().table("results_golden_boot_lock").update(
        {"is_locked": locked}
    ).eq("id", 1).execute()
    load_golden_boot_result_lock.clear()


@st.cache_data(ttl=30)
def load_third_place_advancers_lock() -> bool:
    """Return whether the 3rd place advancers selection is locked."""
    result = get_admin_client().table("results_third_place_advancers_lock").select("is_locked").eq("id", 1).execute()
    return result.data[0]["is_locked"] if result.data else False


def set_third_place_advancers_lock(locked: bool) -> None:
    """Lock or unlock the 3rd place advancers selection. Invalidates the cache."""
    get_admin_client().table("results_third_place_advancers_lock").update(
        {"is_locked": locked}
    ).eq("id", 1).execute()
    load_third_place_advancers_lock.clear()


# ── Group results ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_group_results() -> dict[str, dict]:
    """Return {group_letter: {final_ranking, third_place_advances}} for saved groups."""
    result = (
        get_admin_client()
        .table("results_group_stage")
        .select("group_letter, final_ranking, third_place_advances")
        .execute()
    )
    return {row["group_letter"]: row for row in result.data}


def save_group_results(rows: list[dict]) -> None:
    """Save final group rankings. Does not require 3rd place advancers selection."""
    get_admin_client().table("results_group_stage").upsert(
        rows, on_conflict="group_letter"
    ).execute()
    load_group_results.clear()
    recalculate_all_scores()
    load_leaderboard.clear()


def save_third_place_advancers(tp_results: dict[str, bool]) -> None:
    """Update third_place_advances for all groups. tp_results = {group_letter: bool}."""
    rows = [
        {"group_letter": letter, "third_place_advances": advances}
        for letter, advances in tp_results.items()
    ]
    get_admin_client().table("results_group_stage").upsert(
        rows, on_conflict="group_letter"
    ).execute()
    load_group_results.clear()
    recalculate_all_scores()
    load_leaderboard.clear()


# ── Real bracket ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_real_bracket() -> list[dict]:
    """Return all matchups ordered by round and slot."""
    result = (
        get_admin_client()
        .table("real_bracket")
        .select("id, round, slot, team_a, team_b, winner, is_penalty")
        .order("round")
        .order("slot")
        .execute()
    )
    return result.data


def save_bracket_round(round_code: str, matchups: list[dict]) -> None:
    """Upsert matchups for one round. Each dict must have: slot, team_a, team_b."""
    rows = [{"round": round_code, "slot": m["slot"], "team_a": m["team_a"], "team_b": m["team_b"]} for m in matchups]
    get_admin_client().table("real_bracket").upsert(rows, on_conflict="round,slot").execute()
    load_real_bracket.clear()
    load_bracket_matchups.clear()


def save_match_results(updates: list[dict]) -> None:
    """Update winner + is_penalty for a list of matchups. Each dict: id, winner, is_penalty."""
    client = get_admin_client()
    for upd in updates:
        client.table("real_bracket").update({
            "winner": upd["winner"],
            "is_penalty": upd["is_penalty"],
        }).eq("id", upd["id"]).execute()
    load_real_bracket.clear()
    load_bracket_matchups.clear()
    recalculate_all_scores()
    load_leaderboard.clear()


# ── Player goals ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_player_goals() -> dict[int, int]:
    """Return {player_id: goals_scored} for all stored players."""
    result = (
        get_admin_client()
        .table("results_player_goals")
        .select("player_id, goals_scored")
        .execute()
    )
    return {row["player_id"]: row["goals_scored"] for row in result.data}


@st.cache_data(ttl=30)
def load_unlisted_golden_boot_winner() -> dict | None:
    """Load the current unlisted Golden Boot winner, if any."""
    result = (
        get_admin_client()
        .table("results_unlisted_golden_boot_winner")
        .select("player_name, goals_scored")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_unlisted_golden_boot_winner(player_name: str, goals_scored: int) -> None:
    """Record or update an unlisted player as the Golden Boot winner."""
    existing = load_unlisted_golden_boot_winner()
    if existing:
        # Update the most recent entry
        get_admin_client().table("results_unlisted_golden_boot_winner").update({
            "player_name": player_name,
            "goals_scored": goals_scored,
        }).eq("player_name", existing["player_name"]).execute()
    else:
        # Insert new entry
        get_admin_client().table("results_unlisted_golden_boot_winner").insert({
            "player_name": player_name,
            "goals_scored": goals_scored,
        }).execute()
    load_unlisted_golden_boot_winner.clear()


def save_player_goals(goals: dict[int, int]) -> None:
    """Replace all goal tallies. goals = {player_id: goals_scored}."""
    now = datetime.now(timezone.utc).isoformat()
    client = get_admin_client()
    # Wipe existing and re-insert non-zero entries (simpler, single-admin context)
    client.table("results_player_goals").delete().neq("player_id", 0).execute()
    non_zero = [
        {"player_id": pid, "goals_scored": g, "updated_at": now}
        for pid, g in goals.items() if g > 0
    ]
    if non_zero:
        client.table("results_player_goals").insert(non_zero).execute()
    load_player_goals.clear()
    recalculate_all_scores()
    load_leaderboard.clear()


# ── Bonus correct answers ──────────────────────────────────────────────────────

def save_bonus_correct_options(question_id: int, correct_options: list[str] | None) -> None:
    get_admin_client().table("bonus_question_defs").update({
        "correct_options": correct_options or None,
    }).eq("id", question_id).execute()
    load_bonus_questions.clear()
    recalculate_all_scores()
    load_leaderboard.clear()


# ── User management ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_all_users() -> list[dict]:
    """Return all profiles as [{id, email, display_name}] ordered by display_name."""
    result = (
        get_admin_client()
        .table("profiles")
        .select("id, email, display_name")
        .order("display_name")
        .execute()
    )
    return result.data


def reset_user_picks(user_id: str) -> None:
    """Delete all prediction rows for the given user across every prediction table."""
    client = get_admin_client()
    for table in (
        "predictions_group_stage",
        "predictions_champion",
        "predictions_bracket",
        "predictions_golden_boot",
        "predictions_bonus",
    ):
        client.table(table).delete().eq("user_id", user_id).execute()