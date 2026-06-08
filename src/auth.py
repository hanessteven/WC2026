# Stub — implemented in feature 05 (Authentication)
# Placeholder exports so other modules can import without errors.

from src.config import get_admin_emails


def get_current_user() -> dict | None:
    """Return the authenticated user dict from st.session_state, or None."""
    import streamlit as st
    return st.session_state.get("user")


def is_admin(user: dict | None = None) -> bool:
    """Return True if the given (or current) user is an admin."""
    if user is None:
        user = get_current_user()
    if not user:
        return False
    email = (user.get("email") or "").lower()
    return email in get_admin_emails()


def require_auth() -> dict:
    """Redirect to login if not authenticated. Returns user dict when authenticated."""
    import streamlit as st
    user = get_current_user()
    if not user:
        st.warning("Please sign in to continue.")
        st.stop()
    return user