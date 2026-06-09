"""Admin-only DB helpers — results, locks, bracket, user management.

All writes use the service-role client (bypasses RLS).
Never expose these functions to non-admin users.
"""
from __future__ import annotations

import streamlit as st


# ── Lock state ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_lock_state() -> dict[str, bool]:
    """Return {category: is_locked} for all 9 categories."""
    from src.db import get_admin_client
    result = get_admin_client().table("lock_state").select("category, is_locked").execute()
    return {row["category"]: row["is_locked"] for row in result.data}


def set_lock(category: str, locked: bool) -> None:
    from datetime import datetime, timezone
    from src.auth import get_current_user
    from src.db import get_admin_client
    user = get_current_user()
    get_admin_client().table("lock_state").update({
        "is_locked": locked,
        "locked_at": datetime.now(timezone.utc).isoformat() if locked else None,
        "locked_by": user["email"] if locked and user else None,
    }).eq("category", category).execute()
    load_lock_state.clear()


# ── Group results ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_group_results() -> dict[str, dict]:
    """Return {group_letter: {final_ranking, third_place_advances}} for saved groups."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("results_group_stage")
        .select("group_letter, final_ranking, third_place_advances")
        .execute()
    )
    return {row["group_letter"]: row for row in result.data}


def save_group_results(rows: list[dict]) -> None:
    from src.db import get_admin_client
    get_admin_client().table("results_group_stage").upsert(
        rows, on_conflict="group_letter"
    ).execute()
    load_group_results.clear()


# ── Real bracket ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_real_bracket() -> list[dict]:
    """Return all matchups ordered by round and slot."""
    from src.db import get_admin_client
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
    from src.db import get_admin_client
    from src.predictions import load_bracket_matchups
    rows = [{"round": round_code, "slot": m["slot"], "team_a": m["team_a"], "team_b": m["team_b"]} for m in matchups]
    get_admin_client().table("real_bracket").upsert(rows, on_conflict="round,slot").execute()
    load_real_bracket.clear()
    load_bracket_matchups.clear()


def save_match_results(updates: list[dict]) -> None:
    """Update winner + is_penalty for a list of matchups. Each dict: id, winner, is_penalty."""
    from src.db import get_admin_client
    from src.predictions import load_bracket_matchups
    client = get_admin_client()
    for upd in updates:
        client.table("real_bracket").update({
            "winner": upd["winner"],
            "is_penalty": upd["is_penalty"],
        }).eq("id", upd["id"]).execute()
    load_real_bracket.clear()
    load_bracket_matchups.clear()


# ── Player goals ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_player_goals() -> dict[int, int]:
    """Return {player_id: goals_scored} for all stored players."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("results_player_goals")
        .select("player_id, goals_scored")
        .execute()
    )
    return {row["player_id"]: row["goals_scored"] for row in result.data}


def save_player_goals(goals: dict[int, int]) -> None:
    """Replace all goal tallies. goals = {player_id: goals_scored}."""
    from datetime import datetime, timezone
    from src.db import get_admin_client
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


# ── Bonus correct answers ──────────────────────────────────────────────────────

def save_bonus_correct_options(question_id: int, correct_options: list[str] | None) -> None:
    from src.db import get_admin_client
    get_admin_client().table("bonus_question_defs").update({
        "correct_options": correct_options or None,
    }).eq("id", question_id).execute()
    from src.predictions import load_bonus_questions
    load_bonus_questions.clear()


# ── User management ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_all_users() -> list[dict]:
    """Return all profiles as [{id, email, display_name}] ordered by display_name."""
    from src.db import get_admin_client
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
    from src.db import get_admin_client
    client = get_admin_client()
    for table in (
        "predictions_group_stage",
        "predictions_champion",
        "predictions_bracket",
        "predictions_golden_boot",
        "predictions_bonus",
    ):
        client.table(table).delete().eq("user_id", user_id).execute()