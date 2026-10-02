from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path(__file__).parent / "test.db"
TEST_DB.unlink(missing_ok=True)
os.environ["CMH_ANESTHESIA_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["CMH_ANESTHESIA_TESTING"] = "true"
os.environ["CMH_ANESTHESIA_ADMIN_PASSWORD"] = "Admin-test-2026"
os.environ["CMH_ANESTHESIA_SEED_USER_PASSWORD"] = "Staff-test-2026"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
        for user in db.scalars(select(User)).all():
            user.must_change_password = False
        db.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "Staff-test-2026"})
    assert response.status_code == 200, response.text
