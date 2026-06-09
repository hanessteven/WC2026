"""Integration tests for src/auth.py (register / login / whitelist / admin).

bcrypt is exercised for real; the DB is the in-memory fake. The cookie/session
flow (restore_session, show_login_ui) is UI-bound and out of scope here.
"""
from __future__ import annotations

import bcrypt
import pytest

from src.auth import (
    check_whitelist,
    get_profile,
    is_admin,
    login,
    register,
    set_display_name,
)

WHITELISTED = "friend@test.com"


def _seed_whitelist(db, *emails):
    db.seed("allowed_emails", [{"email": e} for e in emails])


# ── whitelist ─────────────────────────────────────────────────────────────────

def test_check_whitelist_normalizes_case_and_whitespace(fake_db):
    _seed_whitelist(fake_db, "friend@test.com")
    assert check_whitelist("  FRIEND@Test.com ") is True
    assert check_whitelist("stranger@test.com") is False


# ── register ──────────────────────────────────────────────────────────────────

def test_register_creates_profile_with_hashed_password(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    user = register(WHITELISTED, "password123", "Friendly")

    assert user["email"] == WHITELISTED
    row = next(r for r in fake_db.rows("profiles") if r["email"] == WHITELISTED)
    assert row["display_name"] == "Friendly"
    assert row["password_hash"] and row["password_hash"] != "password123"
    assert bcrypt.checkpw(b"password123", row["password_hash"].encode())


def test_register_rejects_non_whitelisted(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    with pytest.raises(PermissionError, match="not_whitelisted"):
        register("stranger@test.com", "password123", "Nope")


def test_register_rejects_duplicate(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    register(WHITELISTED, "password123", "First")
    with pytest.raises(ValueError, match="already_registered"):
        register(WHITELISTED, "different", "Second")


def test_register_claims_legacy_row_without_password(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    fake_db.seed("profiles", [
        {"id": "legacy-1", "email": WHITELISTED, "display_name": None, "password_hash": None},
    ])
    user = register(WHITELISTED, "password123", "Claimed")

    assert user["id"] == "legacy-1"                     # claimed, not duplicated
    assert len([r for r in fake_db.rows("profiles") if r["email"] == WHITELISTED]) == 1
    row = fake_db.rows("profiles")[0]
    assert row["display_name"] == "Claimed"
    assert row["password_hash"]


def test_register_normalizes_email(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    register("  FRIEND@Test.com ", "password123", "Mixed")
    row = fake_db.rows("profiles")[0]
    assert row["email"] == WHITELISTED


# ── login ─────────────────────────────────────────────────────────────────────

def test_login_succeeds_with_correct_password(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    created = register(WHITELISTED, "password123", "Friendly")
    user = login(WHITELISTED, "password123")
    assert user["id"] == created["id"]
    assert user["email"] == WHITELISTED


def test_login_rejects_wrong_password(fake_db):
    _seed_whitelist(fake_db, WHITELISTED)
    register(WHITELISTED, "password123", "Friendly")
    with pytest.raises(ValueError, match="invalid_credentials"):
        login(WHITELISTED, "wrongpass")


def test_login_rejects_unknown_email(fake_db):
    with pytest.raises(ValueError, match="invalid_credentials"):
        login("ghost@test.com", "whatever")


def test_login_rejects_legacy_row_without_password(fake_db):
    fake_db.seed("profiles", [
        {"id": "legacy-1", "email": WHITELISTED, "display_name": "X", "password_hash": None},
    ])
    with pytest.raises(ValueError, match="invalid_credentials"):
        login(WHITELISTED, "password123")


# ── profile helpers ────────────────────────────────────────────────────────

def test_set_display_name_trims_and_persists(fake_db):
    fake_db.seed("profiles", [{"id": "u1", "email": "a@t.com", "display_name": "Old"}])
    set_display_name("u1", "  New Name  ")
    assert fake_db.rows("profiles")[0]["display_name"] == "New Name"


def test_get_profile_returns_row_or_none(fake_db):
    fake_db.seed("profiles", [{"id": "u1", "email": "a@t.com", "display_name": "A"}])
    assert get_profile("u1")["email"] == "a@t.com"
    assert get_profile("missing") is None


# ── admin flag ────────────────────────────────────────────────────────────────

def test_is_admin_matches_configured_emails():
    assert is_admin({"email": "admin@test.com"}) is True
    assert is_admin({"email": "ADMIN@TEST.COM"}) is True   # case-insensitive
    assert is_admin({"email": "user@test.com"}) is False
    assert is_admin({}) is False