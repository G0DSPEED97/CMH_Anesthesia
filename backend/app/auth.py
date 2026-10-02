from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSession

SESSION_COOKIE = "cmh_anesthesia_session"
SESSION_HOURS = int(os.getenv("CMH_ANESTHESIA_SESSION_HOURS", "12"))
COOKIE_SECURE = os.getenv("CMH_ANESTHESIA_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
ROLES = {"admin", "reception", "doctor", "ot_controller", "auditor", "display"}
DUMMY_HASH = "pbkdf2_sha256$600000$00000000000000000000000000000000$e9cf86664f65f6113043257c35469267eafbc9d1b10b175e756e6b5929d836f5"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (TypeError, ValueError):
        return False


def issue_session(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(
        UserSession(
            id=hashlib.sha256(raw.encode()).hexdigest(),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=SESSION_HOURS),
        )
    )
    db.commit()
    return raw


def session_user(db: Session, raw: str | None) -> User | None:
    if not raw:
        return None
    session = db.get(UserSession, hashlib.sha256(raw.encode()).hexdigest())
    if not session or session.expires_at <= utcnow():
        if session:
            db.delete(session)
            db.commit()
        return None
    user = db.get(User, session.user_id)
    return user if user and user.is_active else None


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = session_user(db, request.cookies.get(SESSION_COOKIE))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    if user.must_change_password and request.url.path not in {
        "/api/v1/auth/me",
        "/api/v1/auth/password",
        "/api/v1/auth/logout",
    }:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Change the temporary password before continuing")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permission")
        return user

    return dependency
