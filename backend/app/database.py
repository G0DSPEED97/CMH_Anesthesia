from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def resolve_database_url() -> str:
    value = os.getenv("CMH_ANESTHESIA_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "CMH_ANESTHESIA_DATABASE_URL is required. Run the project launcher to configure PostgreSQL."
        )
    if value.startswith("sqlite") and os.getenv("CMH_ANESTHESIA_TESTING", "").lower() != "true":
        raise RuntimeError("SQLite is supported only by automated tests. Configure PostgreSQL for application use.")
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if not value.startswith(("postgresql+psycopg://", "sqlite")):
        raise RuntimeError("CMH_ANESTHESIA_DATABASE_URL must use PostgreSQL with the psycopg driver.")
    return value


DATABASE_URL = resolve_database_url()


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    hide_parameters=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
