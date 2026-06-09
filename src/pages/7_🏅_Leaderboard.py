import streamlit as st
import pandas as pd

from src.predictions import load_leaderboard

st.title("🏅 Leaderboard")

user = st.session_state.get("user")
profile = st.session_state.get("profile") or {}
current_user_id: str | None = profile.get("id") or (user or {}).get("id")

rows = load_leaderboard()

if not rows:
    st.info("No scores yet — check back once the tournament begins.")
    st.stop()

display_data = []
for row in rows:
    name = ("★ " if row["user_id"] == current_user_id else "") + (row["display_name"] or "—")
    entry: dict = {
        "Rank": row["rank"],
        "Name": name,
        "Total": row["total_pts"],
        "Group": row["group_stage_pts"],
        "Bracket": row["bracket_pts"],
        "Champion": row["champion_pts"],
        "Boot": row["golden_boot_pts"],
        "Bonus": row["bonus_pts"],
    }
    if user:
        entry["Email"] = row["email"]
    display_data.append(entry)

df = pd.DataFrame(display_data)


def _highlight_user(row: pd.Series) -> list[str]:
    name_val = row.get("Name", "")
    if isinstance(name_val, str) and name_val.startswith("★"):
        return ["background-color: #2a4a1a; color: #ffd700"] * len(row)
    return [""] * len(row)


styled = df.style.apply(_highlight_user, axis=1)
st.dataframe(styled, hide_index=True, use_container_width=True)

if not user:
    st.caption("Sign in from the Home page to see email addresses and track your own rank.")