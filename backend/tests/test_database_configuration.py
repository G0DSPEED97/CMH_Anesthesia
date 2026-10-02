from __future__ import annotations

import pytest

from app.database import resolve_database_url


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CMH_ANESTHESIA_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="required"):
        resolve_database_url()


def test_sqlite_is_restricted_to_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CMH_ANESTHESIA_DATABASE_URL", "sqlite:///local.db")
    monkeypatch.delenv("CMH_ANESTHESIA_TESTING", raising=False)
    with pytest.raises(RuntimeError, match="only by automated tests"):
        resolve_database_url()


def test_postgresql_url_is_accepted(monkeypatch: pytest.MonkeyPatch):
    value = "postgresql+psycopg://cmh_anesthesia:secret@127.0.0.1:5432/cmh_anesthesia"
    monkeypatch.setenv("CMH_ANESTHESIA_DATABASE_URL", value)
    monkeypatch.delenv("CMH_ANESTHESIA_TESTING", raising=False)
    assert resolve_database_url() == value


def test_plain_postgresql_url_uses_psycopg(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "CMH_ANESTHESIA_DATABASE_URL",
        "postgresql://cmh_anesthesia:secret@127.0.0.1:5432/cmh_anesthesia",
    )
    monkeypatch.delenv("CMH_ANESTHESIA_TESTING", raising=False)
    assert resolve_database_url().startswith("postgresql+psycopg://")
