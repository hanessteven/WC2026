"""DB helpers for reading and writing prediction data.

All writes go through the service-role admin client (bypasses RLS).
Cache seed/reference data aggressively; clear prediction caches after writes.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.db import get_admin_client
from src.locks import load_lock_state
from src.models import ChampionPick
from src.score_runner import recalculate_user_score


# ── Seed / reference data (cached long — never changes) ──────────────────────

@st.cache_data(ttl=3600)
def load_teams_by_group() -> dict[str, list[dict]]:
    """Return {group_letter: [{name, flag_emoji, id}, ...]} ordered by seed position."""
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
    """Return True if the given lock category is active.

    Reads through the single cached lock-state source so every caller —
    user pages and admin alike — sees the same value. The cache is cleared
    whenever a lock is toggled, so there's no staleness window.
    """
    return bool(load_lock_state().get(category, False))


# ── Group stage predictions ───────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_group_predictions(user_id: str) -> dict[str, dict]:
    """Return {group_letter: {predicted_ranking, third_place_advances}} for this user."""
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
    get_admin_client().table("predictions_group_stage").upsert(
        rows, on_conflict="user_id,group_letter"
    ).execute()
    load_group_predictions.clear()
    recalculate_user_score(user_id)
    load_leaderboard.clear()


# ── Champion pick ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_champion_pick(user_id: str) -> dict | None:
    """Return {champion, dark_horse} for this user, or None if not yet saved."""
    result = (
        get_admin_client()
        .table("predictions_champion")
        .select("champion, dark_horse")
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def save_champion_pick(user_id: str, champion: str, dark_horse: str | None) -> None:
    """Validate and upsert the champion pick row, then invalidate the read cache.

    Constructing ChampionPick enforces the model rules (e.g. dark horse must differ
    from the champion) at the data boundary, not just in the UI.
    """
    ChampionPick(champion=champion, dark_horse=dark_horse)  # raises ValueError if invalid
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
    recalculate_user_score(user_id)
    load_leaderboard.clear()


# ── Golden boot draft ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_players_by_tier() -> dict[int, list[dict]]:
    """Return {tier: [{id, name, team_name, tier, cost}, ...]} ordered by cost desc."""
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
    client = get_admin_client()
    client.table("predictions_golden_boot").delete().eq("user_id", user_id).execute()
    if player_ids:
        client.table("predictions_golden_boot").insert(
            [{"user_id": user_id, "player_id": pid} for pid in player_ids]
        ).execute()
    load_golden_boot_picks.clear()
    recalculate_user_score(user_id)
    load_leaderboard.clear()


# ── Bonus questions ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_bonus_questions() -> list[dict]:
    """Return [{id, question_text, valid_options, point_value, correct_options}, ...] ordered by id."""
    result = (
        get_admin_client()
        .table("bonus_question_defs")
        .select("id, question_text, valid_options, point_value, correct_options")
        .order("id")
        .execute()
    )
    return result.data


@st.cache_data(ttl=10)
def load_bonus_answers(user_id: str) -> dict[int, str]:
    """Return {question_id: chosen_option} for this user."""
    result = (
        get_admin_client()
        .table("predictions_bonus")
        .select("question_id, chosen_option")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["question_id"]: row["chosen_option"] for row in result.data}


# ── Knockout bracket ──────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_bracket_matchups() -> dict[str, list[dict]]:
    """Return {round: [matchup_dicts ordered by slot]} for all rounds with matchups."""
    result = (
        get_admin_client()
        .table("real_bracket")
        .select("id, round, slot, team_a, team_b, winner, is_penalty")
        .order("round")
        .order("slot")
        .execute()
    )
    rounds: dict[str, list[dict]] = {}
    for row in result.data:
        rounds.setdefault(row["round"], []).append(row)
    return rounds


@st.cache_data(ttl=10)
def load_bracket_picks(user_id: str) -> dict[int, str]:
    """Return {matchup_id: predicted_winner} for this user."""
    result = (
        get_admin_client()
        .table("predictions_bracket")
        .select("matchup_id, predicted_winner")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["matchup_id"]: row["predicted_winner"] for row in result.data}


def save_bracket_picks(user_id: str, picks: dict[int, str]) -> None:
    """Upsert bracket picks for this user. picks = {matchup_id: predicted_winner}."""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"user_id": user_id, "matchup_id": mid, "predicted_winner": winner, "updated_at": now}
        for mid, winner in picks.items()
    ]
    get_admin_client().table("predictions_bracket").upsert(
        rows, on_conflict="user_id,matchup_id"
    ).execute()
    load_bracket_picks.clear()
    recalculate_user_score(user_id)
    load_leaderboard.clear()


def save_bonus_answers(user_id: str, answers: dict[int, str]) -> None:
    """Upsert all bonus answers for this user, then invalidate the cache."""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"user_id": user_id, "question_id": qid, "chosen_option": option, "updated_at": now}
        for qid, option in answers.items()
    ]
    get_admin_client().table("predictions_bonus").upsert(
        rows, on_conflict="user_id,question_id"
    ).execute()
    load_bonus_answers.clear()
    recalculate_user_score(user_id)
    load_leaderboard.clear()


# ── Leaderboard ────────────────────────────────────────────────────────────────

def _embedded_profile(raw: dict) -> dict:
    """Normalize the embedded profiles resource (Supabase may return dict or list)."""
    prof = raw.get("profiles") or {}
    if isinstance(prof, list):
        prof = prof[0] if prof else {}
    return prof


def _assemble_leaderboard(raw_rows: list[dict]) -> list[dict]:
    """Pure transform: raw score rows (with embedded profile) → ranked leaderboard.

    Sorted by total_pts desc then display_name asc; tied totals share a rank.
    Kept free of any DB/Streamlit calls so it can be unit-tested directly.
    """
    rows = []
    for r in raw_rows:
        profile = _embedded_profile(r)
        rows.append({
            "user_id": r["user_id"],
            "display_name": profile.get("display_name") or "",
            "email": profile.get("email") or "",
            "total_pts": r.get("total_pts") or 0,
            "group_stage_pts": r.get("group_stage_pts") or 0,
            "bracket_pts": r.get("bracket_pts") or 0,
            "champion_pts": r.get("champion_pts") or 0,
            "golden_boot_pts": r.get("golden_boot_pts") or 0,
            "bonus_pts": r.get("bonus_pts") or 0,
        })
    rows.sort(key=lambda r: (-r["total_pts"], r["display_name"].lower()))
    prev_total: int | None = None
    rank = 0
    for i, row in enumerate(rows):
        if row["total_pts"] != prev_total:
            rank = i + 1
            prev_total = row["total_pts"]
        row["rank"] = rank
    return rows


@st.cache_data(ttl=60)
def load_leaderboard() -> list[dict]:
    """Return leaderboard rows, sorted by total_pts desc then display_name asc.

    Each row: rank, user_id, display_name, email, total_pts, group_stage_pts,
    bracket_pts, champion_pts, golden_boot_pts, bonus_pts.
    Tied users share the same rank number.
    """
    result = (
        get_admin_client()
        .table("scores")
        .select(
            "user_id, total_pts, group_stage_pts, bracket_pts, "
            "champion_pts, golden_boot_pts, bonus_pts, "
            "profiles(display_name, email)"
        )
        .execute()
    )
    return _assemble_leaderboard(result.data)