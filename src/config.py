import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Load a config value, preferring st.secrets then env vars. Fails fast if missing."""
    # Try Streamlit secrets first (works on Community Cloud and local .streamlit/secrets.toml)
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required config: '{key}'. "
            f"Set it in .streamlit/secrets.toml or as an environment variable."
        )
    return value


def get_supabase_url() -> str:
    return _require("SUPABASE_URL")


def get_supabase_key() -> str:
    return _require("SUPABASE_KEY")


def get_admin_emails() -> list[str]:
    raw = _require("ADMIN_EMAILS")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def get_supabase_service_key() -> str:
    return _require("SUPABASE_SERVICE_KEY")


def get_app_url() -> str:
    return _require("APP_URL").rstrip("/")