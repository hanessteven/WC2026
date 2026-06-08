"""
Authentication — magic-link OTP sign-in with email whitelist.
Uses Supabase email OTP (6-digit code). No redirect URL needed.
"""
from __future__ import annotations

import streamlit as st
from supabase import create_client

from src.config import get_admin_emails, get_supabase_key, get_supabase_url


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


def send_otp(email: str) -> None:
    """Send a 6-digit OTP code to the given email via Supabase auth."""
    _auth_client().auth.sign_in_with_otp({"email": email.strip().lower()})


def verify_otp(email: str, token: str) -> dict:
    """Verify the OTP code. Returns a user dict on success, raises on failure."""
    client = _auth_client()
    response = client.auth.verify_otp(
        {"email": email.strip().lower(), "token": token.strip(), "type": "email"}
    )
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


# ── Login UI ──────────────────────────────────────────────────────────────────

def show_login_ui() -> None:
    """Render the 2-step email OTP sign-in form."""
    st.title("⚽ WC 2026 Predictor")

    step = st.session_state.get("auth_step", "email")

    if step == "email":
        st.subheader("Sign in")
        st.caption("Enter your email and we'll send you a 6-digit code.")
        with st.form("login_email_form"):
            email = st.text_input("Email address")
            submitted = st.form_submit_button("Send Code", use_container_width=True)

        if submitted:
            if not email.strip():
                st.warning("Please enter your email address.")
            elif not check_whitelist(email):
                st.error("Sorry, that email isn't on the guest list for this app.")
            else:
                try:
                    send_otp(email)
                    st.session_state.auth_step = "otp"
                    st.session_state.auth_email = email.strip().lower()
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't send code: {e}")

    elif step == "otp":
        email = st.session_state.get("auth_email", "")
        st.subheader("Check your inbox")
        st.info(f"Code sent to **{email}**. Enter it below — it expires in 10 minutes.")

        with st.form("login_otp_form"):
            token = st.text_input("6-digit code", max_chars=6, placeholder="123456")
            submitted = st.form_submit_button("Verify Code", use_container_width=True)

        if submitted:
            if not token.strip():
                st.warning("Please enter the code from your email.")
            else:
                try:
                    user = verify_otp(email, token)
                    st.session_state.user = user
                    st.session_state.profile = get_profile(user["id"])
                    # Clear sign-in flow state
                    st.session_state.pop("auth_step", None)
                    st.session_state.pop("auth_email", None)
                    st.rerun()
                except Exception:
                    st.error("Invalid or expired code. Please try again.")

        if st.button("Use a different email", use_container_width=True):
            st.session_state.pop("auth_step", None)
            st.session_state.pop("auth_email", None)
            st.rerun()


def require_auth() -> dict:
    """Return the current user dict, or show login UI and stop."""
    user = get_current_user()
    if not user:
        show_login_ui()
        st.stop()
    return user