"""
Authentication — PKCE magic-link sign-in with email whitelist.
Supabase sends a link with ?token_hash= query param; Streamlit reads it server-side.
"""
from __future__ import annotations

import streamlit as st
from supabase import create_client

from src.config import get_admin_emails, get_app_url, get_supabase_key, get_supabase_url


def _auth_client():
    """Fresh Supabase client for auth operations.
    NOT cached — auth state must not bleed between users on a shared instance."""
    return create_client(get_supabase_url(), get_supabase_key())


# ── Core auth logic ───────────────────────────────────────────────────────────

def check_whitelist(email: str) -> bool:
    """Return True if the email is in the allowed_emails table."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("allowed_emails")
        .select("email")
        .eq("email", email.strip().lower())
        .execute()
    )
    return len(result.data) > 0


def send_magic_link(email: str) -> None:
    """Send a sign-in link to the given email via Supabase PKCE flow.
    The link lands back at APP_URL with ?token_hash=... which we read server-side."""
    _auth_client().auth.sign_in_with_otp({
        "email": email.strip().lower(),
        "options": {"email_redirect_to": get_app_url()},
    })


def verify_token_hash(token_hash: str) -> dict:
    """Exchange a token_hash (from the magic link query param) for a user session."""
    client = _auth_client()
    response = client.auth.verify_otp({
        "token_hash": token_hash,
        "type": "email",
    })
    return {
        "id": str(response.user.id),
        "email": response.user.email,
    }


def get_profile(user_id: str) -> dict | None:
    """Fetch the profiles row for a user. Returns None if not found."""
    from src.db import get_admin_client
    result = (
        get_admin_client()
        .table("profiles")
        .select("id, email, display_name, created_at")
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def set_display_name(user_id: str, display_name: str) -> None:
    """Upsert the display_name on a user's profile row."""
    from src.db import get_admin_client
    get_admin_client().table("profiles").update(
        {"display_name": display_name.strip()}
    ).eq("id", user_id).execute()


def get_current_user() -> dict | None:
    """Return the authenticated user dict from session state, or None."""
    return st.session_state.get("user")


def is_admin(user: dict | None = None) -> bool:
    """Return True if the given (or current) user is an admin."""
    if user is None:
        user = get_current_user()
    if not user:
        return False
    return user.get("email", "").lower() in get_admin_emails()


def logout() -> None:
    """Clear all auth state from the session."""
    for key in ("user", "profile", "auth_step", "auth_email"):
        st.session_state.pop(key, None)


def handle_magic_link_callback() -> bool:
    """
    If ?token_hash= is present in the URL, verify it and store the user in session.
    Returns True if a callback was handled (caller should st.rerun()).
    """
    token_hash = st.query_params.get("token_hash")
    if not token_hash:
        return False

    # Clear the token from the URL immediately so it can't be replayed on refresh
    st.query_params.clear()

    try:
        user = verify_token_hash(token_hash)
        st.session_state.user = user
        st.session_state.profile = get_profile(user["id"])
    except Exception:
        st.error("Sign-in link is invalid or expired. Please request a new one.")

    return True


# ── Login UI ──────────────────────────────────────────────────────────────────

def show_login_ui() -> None:
    """Render the email sign-in form (magic link flow)."""
    st.title("⚽ WC 2026 Predictor")
    st.subheader("Sign in")
    st.caption("Enter your email and we'll send you a sign-in link.")

    with st.form("login_email_form"):
        email = st.text_input("Email address")
        submitted = st.form_submit_button("Send Sign-in Link", use_container_width=True)

    if submitted:
        if not email.strip():
            st.warning("Please enter your email address.")
        elif not check_whitelist(email):
            st.error("Sorry, that email isn't on the guest list for this app.")
        else:
            try:
                send_magic_link(email)
                st.success(f"Link sent to **{email.strip()}** — check your inbox and click it to sign in.")
            except Exception as e:
                st.error(f"Couldn't send link: {e}")


def require_auth() -> dict:
    """Return the current user dict, or show login UI and stop."""
    user = get_current_user()
    if not user:
        show_login_ui()
        st.stop()
    return user