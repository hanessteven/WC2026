"""Lock state — read/write for the 9 prediction-category locks.

Kept in its own module so predictions.py and admin.py can both
import it without creating a circular dependency between each other.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.auth import get_current_user
from src.db import get_admin_client


@st.cache_data(ttl=30)
def load_lock_state() -> dict[str, bool]:
    """Return {category: is_locked} for all 9 categories."""
    result = get_admin_client().table("lock_state").select("category, is_locked").execute()
    return {row["category"]: row["is_locked"] for row in result.data}


def set_lock(category: str, locked: bool) -> None:
    """Toggle a lock and invalidate the cached state."""
    user = get_current_user()
    get_admin_client().table("lock_state").update({
        "is_locked": locked,
        "locked_at": datetime.now(timezone.utc).isoformat() if locked else None,
        "locked_by": user["email"] if locked and user else None,
    }).eq("category", category).execute()
    load_lock_state.clear()