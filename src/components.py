"""Shared UI components rendered across multiple pages."""
import streamlit as st
from src.auth import get_current_user, logout


def render_sidebar() -> None:
    """Render user info and sign-out button in the sidebar."""
    user = get_current_user()
    if not user:
        return

    with st.sidebar:
        profile = st.session_state.get("profile")
        display_name = (profile or {}).get("display_name") or user.get("email", "")
        st.markdown(f"Signed in as **{display_name}**")
        st.divider()

        if st.button("Sign out", use_container_width=True):
            logout()
            st.rerun()