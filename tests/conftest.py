"""Shared test fixtures + an in-memory fake Supabase client.

The fake mimics the subset of the supabase-py query-builder chain the app uses, so
integration tests can exercise src/score_runner.py, src/predictions.py, src/admin.py
and src/auth.py without a network or a real database.
"""
from __future__ import annotations

import logging
import os
from uuid import uuid4

import pytest

# Provide dummy config so any accidental real config read doesn't explode.
# (Integration tests patch get_admin_client, so the real client is never built.)
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")
os.environ.setdefault("COOKIE_SECRET", "test-cookie-secret")

# Silence Streamlit's "missing ScriptRunContext" warnings emitted when cached
# functions run outside a real script run.
logging.getLogger("streamlit").setLevel(logging.ERROR)


# ── In-memory fake Supabase ──────────────────────────────────────────────────

class _Result:
    def __init__(self, data: list[dict]):
        self.data = data


class _Query:
    """A single table query/mutation builder backed by the shared store."""

    def __init__(self, store: dict[str, list[dict]], table: str):
        self._store = store
        self._table = table
        self._filters: list[tuple[str, str, object]] = []
        self._orders: list[tuple[str, bool]] = []
        self._op: str | None = None
        self._payload = None
        self._on_conflict: str | None = None

    # reads / column projection (projection is ignored — we return whole rows)
    def select(self, *_cols, **_kw) -> "_Query":
        self._op = self._op or "select"
        return self

    # filters
    def eq(self, col: str, val) -> "_Query":
        self._filters.append(("eq", col, val)); return self

    def neq(self, col: str, val) -> "_Query":
        self._filters.append(("neq", col, val)); return self

    def in_(self, col: str, vals) -> "_Query":
        self._filters.append(("in", col, list(vals))); return self

    def order(self, col: str, desc: bool = False) -> "_Query":
        self._orders.append((col, desc)); return self

    # writes
    def insert(self, rows) -> "_Query":
        self._op = "insert"
        self._payload = rows if isinstance(rows, list) else [rows]
        return self

    def upsert(self, rows, on_conflict: str | None = None) -> "_Query":
        self._op = "upsert"
        self._payload = rows if isinstance(rows, list) else [rows]
        self._on_conflict = on_conflict
        return self

    def update(self, values: dict) -> "_Query":
        self._op = "update"
        self._payload = values
        return self

    def delete(self) -> "_Query":
        self._op = "delete"
        return self

    # ── execution ───────────────────────────────────────────────────────────
    def _matches(self, row: dict) -> bool:
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "neq" and row.get(col) == val:
                return False
            if op == "in" and row.get(col) not in val:
                return False
        return True

    def _assign_id(self, row: dict) -> dict:
        """Simulate a DB-generated id for inserts that omit one."""
        if "id" not in row or row["id"] is None:
            row = {**row, "id": str(uuid4())}
        return row

    def execute(self) -> _Result:
        rows = self._store.setdefault(self._table, [])

        if self._op == "select":
            out = [dict(r) for r in rows if self._matches(r)]
            for col, desc in reversed(self._orders):
                out.sort(key=lambda r: r.get(col), reverse=desc)
            return _Result(out)

        if self._op == "insert":
            inserted = [self._assign_id(dict(r)) for r in self._payload]
            rows.extend(inserted)
            return _Result([dict(r) for r in inserted])

        if self._op == "upsert":
            keys = [k.strip() for k in (self._on_conflict or "").split(",") if k.strip()]
            written = []
            for new in self._payload:
                if keys:
                    idx = next(
                        (i for i, r in enumerate(rows)
                         if all(r.get(k) == new.get(k) for k in keys)),
                        None,
                    )
                    if idx is not None:
                        rows[idx] = {**rows[idx], **new}
                        written.append(dict(rows[idx]))
                        continue
                stored = self._assign_id(dict(new))
                rows.append(stored)
                written.append(dict(stored))
            return _Result(written)

        if self._op == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self._payload)
                    updated.append(dict(r))
            return _Result(updated)

        if self._op == "delete":
            removed = [dict(r) for r in rows if self._matches(r)]
            self._store[self._table] = [r for r in rows if not self._matches(r)]
            return _Result(removed)

        return _Result([])


class FakeSupabase:
    """Minimal in-memory stand-in for a supabase-py Client."""

    def __init__(self, store: dict[str, list[dict]] | None = None):
        self.store: dict[str, list[dict]] = store if store is not None else {}

    def table(self, name: str) -> _Query:
        return _Query(self.store, name)

    # test helpers
    def seed(self, table: str, rows: list[dict]) -> "FakeSupabase":
        self.store.setdefault(table, []).extend(dict(r) for r in rows)
        return self

    def rows(self, table: str) -> list[dict]:
        return self.store.get(table, [])


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_streamlit_caches():
    """Reset all @st.cache_data caches between tests so reads don't leak."""
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def fake_db(monkeypatch) -> FakeSupabase:
    """A FakeSupabase wired in as the admin client for every module that uses it.

    Patches both src.db (the source) and every module that binds get_admin_client
    at module level via 'from src.db import get_admin_client', since those modules
    hold their own local name binding that isn't updated by patching src.db alone.
    """
    db = FakeSupabase()
    for mod in (
        "src.db",
        "src.auth",
        "src.locks",
        "src.predictions",
        "src.admin",
        "src.score_runner",
    ):
        monkeypatch.setattr(f"{mod}.get_admin_client", lambda: db)
    return db