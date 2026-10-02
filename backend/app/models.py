from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Rank(Base):
    __tablename__ = "ranks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    label: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(40))
    sort_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    service_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    rank_code: Mapped[str] = mapped_column(String(30), ForeignKey("ranks.code"))
    name: Mapped[str] = mapped_column(String(160), index=True)
    unit: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    rank: Mapped[Rank] = relationship(lazy="joined")


class DailyCounter(Base):
    __tablename__ = "daily_counters"

    counter_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class AnesthesiaCase(Base):
    __tablename__ = "anesthesia_cases"
    __table_args__ = (
        UniqueConstraint("token_date", "token_sequence", name="uq_case_daily_token"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    token_date: Mapped[date] = mapped_column(Date, index=True)
    token_sequence: Mapped[int] = mapped_column(Integer)
    token_number: Mapped[str] = mapped_column(String(30), index=True)
    proposed_surgery: Mapped[str] = mapped_column(String(240))
    proposed_anesthetic: Mapped[str] = mapped_column(String(80))
    consultation_status: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    scheduled_ot_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    ot_serial: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ot_table: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ward: Mapped[str | None] = mapped_column(String(80), nullable=True)
    disease: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation: Mapped[str | None] = mapped_column(String(240), nullable=True)
    surgeon: Mapped[str | None] = mapped_column(String(160), nullable=True)
    anesthesiologist: Mapped[str | None] = mapped_column(String(160), nullable=True)
    asa_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ot_status: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    status_note: Mapped[str | None] = mapped_column(String(240), nullable=True)
    token_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    form_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    patient: Mapped[Patient] = relationship(lazy="joined")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(String(240))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
