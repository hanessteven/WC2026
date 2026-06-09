"""Upfront Champion Pick — who wins the tournament, plus an optional dark horse."""
import streamlit as st

from src.auth import get_current_user
from src.predictions import (
    is_locked,
    load_champion_pick,
    load_teams_by_group,
    save_champion_pick,
)

NO_DARK_HORSE = "— No dark horse pick —"

user = get_current_user()

st.title("⭐ Champion Pick")
st.caption(
    "Your long-range prediction, locked at tournament start. "
    "**13 pts** for the correct champion · **3 pts** if your dark horse reaches the quarterfinals."
)

locked = is_locked("champion")
if locked:
    st.warning("🔒 Champion pick is locked — shown read-only.")

# ── Build team lists with flags ───────────────────────────────────────────────
teams_by_group = load_teams_by_group()
all_team_dicts = [t for group in teams_by_group.values() for t in group]
all_teams = sorted(t["name"] for t in all_team_dicts)
dark_horse_teams = sorted(
    t["name"] for t in all_team_dicts if t.get("is_dark_horse_eligible", True)
)
flag_map = {t["name"]: t.get("flag_emoji") or "" for t in all_team_dicts}


def fmt(name: str) -> str:
    if name == NO_DARK_HORSE:
        return name
    return f"{flag_map.get(name, '')} {name}".strip()


# ── Load existing picks ────────────────────────────────────────────────────────
existing = load_champion_pick(user["id"])
saved_champion = existing["champion"] if existing else None
saved_dark_horse = existing.get("dark_horse") if existing else None

# ── Champion selectbox ─────────────────────────────────────────────────────────
st.subheader("Who wins the 2026 World Cup?")
champ_idx = all_teams.index(saved_champion) if saved_champion in all_teams else 0
champion = st.selectbox(
    "Champion",
    options=all_teams,
    index=champ_idx,
    format_func=fmt,
    disabled=locked,
    key="champion_pick",
)

# ── Dark horse selectbox ───────────────────────────────────────────────────────
st.subheader("Dark horse (optional)")
st.caption(
    "Pick a surprise team you think will reach the quarterfinals. "
    "Tournament favourites are excluded — this has to be a genuine long shot."
)

dh_options = [NO_DARK_HORSE] + dark_horse_teams
dh_idx = (
    dh_options.index(saved_dark_horse)
    if saved_dark_horse and saved_dark_horse in dh_options
    else 0
)
dark_horse_raw = st.selectbox(
    "Dark horse",
    options=dh_options,
    index=dh_idx,
    format_func=fmt,
    disabled=locked,
    key="dark_horse_pick",
)
dark_horse = None if dark_horse_raw == NO_DARK_HORSE else dark_horse_raw

if dark_horse and dark_horse == champion:
    st.warning("Your dark horse can't be the same team as your champion.")

# ── Current picks summary (always visible) ────────────────────────────────────
if existing:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Champion pick", fmt(saved_champion) if saved_champion else "—")
    with c2:
        st.metric("Dark horse", fmt(saved_dark_horse) if saved_dark_horse else "None")

# ── Save ───────────────────────────────────────────────────────────────────────
if not locked:
    st.divider()
    if st.button("💾 Save Pick", type="primary", use_container_width=True):
        errors: list[str] = []
        if dark_horse and dark_horse == champion:
            errors.append("Champion and dark horse must be different teams.")

        if errors:
            for msg in errors:
                st.error(msg)
        else:
            try:
                save_champion_pick(user["id"], champion, dark_horse)
                st.success("✅ Pick saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")