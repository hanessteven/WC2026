"""
Authentication — self-contained email + password sign-in with an email whitelist.

No external auth provider, no SMTP. Friends self-register (gated by the
allowed_emails whitelist), passwords are bcrypt-hashed in the profiles table,
and the session is persisted in a signed cookie so it survives a refresh.
"""
from __future__ import annotations

import bcrypt
import streamlit as st
from itsdangerous import URLSafeTimedSerializer

from src.config import get_admin_emails, get_cookie_secret
from src.db import get_admin_client

COOKIE_NAME = "wc2026_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days, in seconds


# ── Whitelist + profile lookups ───────────────────────────────────────────────

def check_whitelist(email: str) -> bool:
    """Return True if the email is in the allowed_emails table."""
    result = (
        get_admin_client()
        .table("allowed_emails")
        .select("email")
        .eq("email", email.strip().lower())
        .execute()
    )
    return len(result.data) > 0


def _get_profile_by_email(email: str) -> dict | None:
    """Fetch a full profile row (incl. password_hash) by email. None if absent."""
    result = (
        get_admin_client()
        .table("profiles")
        .select("id, email, display_name, password_hash, created_at")
        .eq("email", email.strip().lower())
        .execute()
    )
    return result.data[0] if result.data else None


def get_profile(user_id: str) -> dict | None:
    """Fetch the public profile row for a user (no password_hash). None if absent."""
    result = (
        get_admin_client()
        .table("profiles")
        .select("id, email, display_name, created_at")
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def set_display_name(user_id: str, display_name: str) -> None:
    """Update the display_name on a user's profile row."""
    get_admin_client().table("profiles").update(
        {"display_name": display_name.strip()}
    ).eq("id", user_id).execute()


# ── Register + login ──────────────────────────────────────────────────────────

def register(email: str, password: str, display_name: str) -> dict:
    """Create (or claim) a profile for a whitelisted email. Returns the user dict.

    Raises PermissionError if not whitelisted, ValueError if already registered.
    A legacy profile row with no password_hash (left over from the old auth
    flow) is claimed rather than duplicated.
    """
    email = email.strip().lower()
    if not check_whitelist(email):
        raise PermissionError("not_whitelisted")

    existing = _get_profile_by_email(email)
    if existing and existing.get("password_hash"):
        raise ValueError("already_registered")

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    client = get_admin_client()
    if existing:  # claim the legacy row
        client.table("profiles").update(
            {"password_hash": pw_hash, "display_name": display_name.strip()}
        ).eq("id", existing["id"]).execute()
        user_id = existing["id"]
    else:
        result = client.table("profiles").insert(
            {"email": email, "display_name": display_name.strip(), "password_hash": pw_hash}
        ).execute()
        user_id = result.data[0]["id"]

    return {"id": str(user_id), "email": email}


def login(email: str, password: str) -> dict:
    """Verify credentials. Returns the user dict, or raises ValueError on failure."""
    prof = _get_profile_by_email(email)
    if not prof or not prof.get("password_hash"):
        raise ValueError("invalid_credentials")
    if not bcrypt.checkpw(password.encode("utf-8"), prof["password_hash"].encode("utf-8")):
        raise ValueError("invalid_credentials")
    return {"id": str(prof["id"]), "email": prof["email"]}


# ── Session state + admin flag ────────────────────────────────────────────────

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


def _establish_session(user: dict) -> None:
    """Store the user in session state, warm the profile cache, set the cookie."""
    st.session_state["user"] = user
    st.session_state["profile"] = get_profile(user["id"])
    st.session_state["_cookie_checked"] = True
    _write_session_cookie(user)


def logout() -> None:
    """Clear all auth state from the session and the persistent cookie."""
    _clear_session_cookie()
    for key in ("user", "profile"):
        st.session_state.pop(key, None)


# ── Signed-cookie persistence ─────────────────────────────────────────────────
# All cookie operations are best-effort: if the cookie component misbehaves we
# fall back to a session-only login (you'd re-login after a full refresh) rather
# than crashing.

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_cookie_secret(), salt="wc2026-session")


def _cookie_controller():
    """The single CookieController instance for this script run (or None)."""
    return st.session_state.get("_cookie_ctrl")


def _write_session_cookie(user: dict) -> None:
    ctrl = _cookie_controller()
    if ctrl is None:
        return
    token = _serializer().dumps({"id": user["id"], "email": user["email"]})
    try:
        try:
            ctrl.set(COOKIE_NAME, token, max_age=COOKIE_MAX_AGE)
        except TypeError:
            ctrl.set(COOKIE_NAME, token)
    except Exception:
        pass


def _clear_session_cookie() -> None:
    ctrl = _cookie_controller()
    if ctrl is None:
        return
    try:
        ctrl.remove(COOKIE_NAME)
    except Exception:
        pass


def restore_session() -> None:
    """Rehydrate the session from the cookie. Call once at the top of every run.

    Idempotent: a no-op once a user is already in session state. Creates the
    single per-run CookieController instance that the write/clear helpers reuse.
    """
    # Establish exactly one CookieController for this script run.
    try:
        from streamlit_cookies_controller import CookieController
        st.session_state["_cookie_ctrl"] = CookieController()
    except Exception:
        st.session_state["_cookie_ctrl"] = None

    if st.session_state.get("user"):
        return

    ctrl = st.session_state.get("_cookie_ctrl")
    if ctrl is None:
        return

    try:
        raw = ctrl.get(COOKIE_NAME)
    except Exception:
        raw = None

    if not raw:
        # The component may not have synced cookies on first mount. Give it
        # exactly one rerun to deliver them, then accept "no cookie".
        if not st.session_state.get("_cookie_checked"):
            st.session_state["_cookie_checked"] = True
            st.rerun()
        return

    try:
        data = _serializer().loads(raw, max_age=COOKIE_MAX_AGE)
        st.session_state["user"] = {"id": data["id"], "email": data["email"]}
        st.session_state["profile"] = get_profile(data["id"])
        st.session_state["_cookie_checked"] = True
    except Exception:
        _clear_session_cookie()  # invalid or expired


# ── Login / register UI ───────────────────────────────────────────────────────

def show_login_ui() -> None:
    """Render the Sign in / Register tabs."""
    st.title("⚽ WC 2026 Predictor")
    sign_in_tab, register_tab = st.tabs(["Sign in", "Register"])

    with sign_in_tab:
        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if not email.strip() or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    user = login(email, password)
                    _establish_session(user)
                    st.rerun()
                except ValueError:
                    st.error("Incorrect email or password.")

    with register_tab:
        st.caption("First time here? Register with your whitelisted email.")
        with st.form("register_form"):
            r_email = st.text_input("Email address", key="reg_email")
            r_name = st.text_input("Display name (shown on the leaderboard)", max_chars=30)
            r_pw = st.text_input("Password (8+ characters)", type="password")
            r_pw2 = st.text_input("Confirm password", type="password")
            r_submitted = st.form_submit_button("Create account", use_container_width=True)
        if r_submitted:
            if not r_email.strip() or not r_name.strip() or not r_pw:
                st.warning("Fill in every field.")
            elif len(r_pw) < 8:
                st.warning("Password must be at least 8 characters.")
            elif r_pw != r_pw2:
                st.warning("Passwords don't match.")
            else:
                try:
                    user = register(r_email, r_pw, r_name)
                    _establish_session(user)
                    st.rerun()
                except PermissionError:
                    st.error("Sorry, that email isn't on the guest list for this app.")
                except ValueError:
                    st.error("That email is already registered — switch to the Sign in tab.")


def require_auth() -> dict:
    """Return the current user dict, or restore/show login and stop."""
    restore_session()
    user = get_current_user()
    if not user:
        show_login_ui()
        st.stop()
    return user