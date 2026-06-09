import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.auth import (
    get_current_user,
    get_profile,
    handle_magic_link_callback,
    set_display_name,
    show_login_ui,
)
from src.components import render_sidebar

st.set_page_config(
    page_title="WC 2026 Predictor",
    page_icon="⚽",
    layout="centered",
)

# Handle magic link callback (?token_hash= in URL) before anything else
if handle_magic_link_callback():
    st.rerun()

user = get_current_user()

if not user:
    show_login_ui()
    st.stop()

# ── First-login: prompt for display name ─────────────────────────────────────
profile = st.session_state.get("profile") or get_profile(user["id"])
st.session_state["profile"] = profile  # keep cache warm

if not profile or not profile.get("display_name"):
    st.title("⚽ Welcome!")
    st.write("Before you dive in, what should we call you on the leaderboard?")
    with st.form("display_name_form"):
        name = st.text_input("Display name", max_chars=30)
        submitted = st.form_submit_button("Save & Continue", use_container_width=True)
    if submitted and name.strip():
        set_display_name(user["id"], name.strip())
        st.session_state["profile"] = {**(profile or {}), "display_name": name.strip()}
        st.rerun()
    st.stop()

# ── Authenticated home ────────────────────────────────────────────────────────
render_sidebar()

display_name = profile.get("display_name", user["email"])
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