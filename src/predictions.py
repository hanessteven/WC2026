"""DB helpers for reading and writing prediction data.

All writes go through the service-role admin client (bypasses RLS).
Cache seed/reference data aggressively; clear prediction caches after writes.
"""
from __future__ import annotations

import streamlit as st


# ── Seed / reference data (cached long — never changes) ──────────────────────

@st.cache_data(ttl=3600)
def load_teams_by_group() -> dict[str, list[dict]]:
    """Return {group_letter: [{name, flag_emoji, id}, ...]} ordered by seed position."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("seed_teams")
        .select("id, name, group_letter, flag_emoji, is_dark_horse_eligible")
        .order("id")
        .execute()
    )
    groups: dict[str, list[dict]] = {}
    for row in result.data:
        groups.setdefault(row["group_letter"], []).append(row)
    return groups


# ── Lock state ────────────────────────────────────────────────────────────────

def is_locked(category: str) -> bool:
    """Return True if the given lock category is active."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("lock_state")
        .select("is_locked")
        .eq("category", category)
        .execute()
    )
    return bool(result.data and result.data[0]["is_locked"])


# ── Group stage predictions ───────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_group_predictions(user_id: str) -> dict[str, dict]:
    """Return {group_letter: {predicted_ranking, third_place_advances}} for this user."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("predictions_group_stage")
        .select("group_letter, predicted_ranking, third_place_advances")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["group_letter"]: row for row in result.data}


def save_group_predictions(user_id: str, rows: list[dict]) -> None:
    """Upsert all group prediction rows, then invalidate the read cache."""
    from src.db import get_admin_client
    get_admin_client().table("predictions_group_stage").upsert(
        rows, on_conflict="user_id,group_letter"
    ).execute()
    load_group_predictions.clear()


# ── Champion pick ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_champion_pick(user_id: str) -> dict | None:
    """Return {champion, dark_horse} for this user, or None if not yet saved."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("predictions_champion")
        .select("champion, dark_horse")
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def save_champion_pick(user_id: str, champion: str, dark_horse: str | None) -> None:
    """Upsert the champion pick row, then invalidate the read cache."""
    from datetime import datetime, timezone
    from src.db import get_admin_client
    get_admin_client().table("predictions_champion").upsert(
        {
            "user_id": user_id,
            "champion": champion,
            "dark_horse": dark_horse,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id",
    ).execute()
    load_champion_pick.clear()


# ── Golden boot draft ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_players_by_tier() -> dict[int, list[dict]]:
    """Return {tier: [{id, name, team_name, tier, cost}, ...]} ordered by cost desc."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("seed_players")
        .select("id, name, team_name, tier, cost")
        .order("cost", desc=True)
        .execute()
    )
    tiers: dict[int, list[dict]] = {}
    for row in result.data:
        tiers.setdefault(row["tier"], []).append(row)
    return tiers


@st.cache_data(ttl=10)
def load_golden_boot_picks(user_id: str) -> set[int]:
    """Return the set of player IDs the user has drafted."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("predictions_golden_boot")
        .select("player_id")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["player_id"] for row in result.data}


def save_golden_boot_picks(user_id: str, player_ids: list[int]) -> None:
    """Replace all golden boot picks for this user, then invalidate the cache."""
    from src.db import get_admin_client
    client = get_admin_client()
    client.table("predictions_golden_boot").delete().eq("user_id", user_id).execute()
    if player_ids:
        client.table("predictions_golden_boot").insert(
            [{"user_id": user_id, "player_id": pid} for pid in player_ids]
        ).execute()
    load_golden_boot_picks.clear()


# ── Bonus questions ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_bonus_questions() -> list[dict]:
    """Return [{id, question_text, valid_options, point_value}, ...] ordered by id."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("bonus_question_defs")
        .select("id, question_text, valid_options, point_value")
        .order("id")
        .execute()
    )
    return result.data


@st.cache_data(ttl=10)
def load_bonus_answers(user_id: str) -> dict[int, str]:
    """Return {question_id: chosen_option} for this user."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("predictions_bonus")
        .select("question_id, chosen_option")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["question_id"]: row["chosen_option"] for row in result.data}


def save_bonus_answers(user_id: str, answers: dict[int, str]) -> None:
    """Upsert all bonus answers for this user, then invalidate the cache."""
    from datetime import datetime, timezone
    from src.db import get_admin_client
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"user_id": user_id, "question_id": qid, "chosen_option": option, "updated_at": now}
        for qid, option in answers.items()
    ]
    get_admin_client().table("predictions_bonus").upsert(
        rows, on_conflict="user_id,question_id"
    ).execute()
    load_bonus_answers.clear()