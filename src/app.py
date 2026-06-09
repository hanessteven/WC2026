import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.auth import (
    get_current_user,
    get_profile,
    restore_session,
    show_login_ui,
)
from src.components import render_sidebar

st.set_page_config(
    page_title="WC 2026 Predictor",
    page_icon="⚽",
    layout="centered",
)

# Rehydrate the session from the persistent cookie before anything else.
restore_session()

user = get_current_user()

if not user:
    show_login_ui()
    st.stop()

# ── Authenticated home ────────────────────────────────────────────────────────
render_sidebar()

profile = st.session_state.get("profile") or get_profile(user["id"])
st.session_state["profile"] = profile  # keep cache warm
display_name = (profile or {}).get("display_name") or user["email"]
st.title("⚽ WC 2026 Predictor")
st.success(f"Welcome back, **{display_name}**!")
st.markdown(
    "Use the sidebar to navigate to your predictions.\n\n"
    "**Sections:**\n"
    "- 🏆 Group Stage predictions\n"
    "- ⭐ Champion Pick\n"
    "- ⚽ Golden Boot Draft\n"
    "- ❓ Bonus Questions\n"
    "- 📊 Bracket\n"
    "- 🥇 Leaderboard"
)