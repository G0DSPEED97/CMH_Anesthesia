from __future__ import annotations

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import AppSetting, Rank, User

RANKS = [
    ("GEN", "General", "Commissioned Officer"),
    ("LT_GEN", "Lieutenant General", "Commissioned Officer"),
    ("MAJ_GEN", "Major General", "Commissioned Officer"),
    ("BRIG_GEN", "Brigadier General", "Commissioned Officer"),
    ("COL", "Colonel", "Commissioned Officer"),
    ("LT_COL", "Lieutenant Colonel", "Commissioned Officer"),
    ("MAJ", "Major", "Commissioned Officer"),
    ("CAPT", "Captain", "Commissioned Officer"),
    ("LT", "Lieutenant", "Commissioned Officer"),
    ("2LT", "Second Lieutenant", "Commissioned Officer"),
    ("HON_CAPT", "Honorary Captain", "Junior Commissioned Officer"),
    ("HON_LT", "Honorary Lieutenant", "Junior Commissioned Officer"),
    ("MWO", "Master Warrant Officer", "Junior Commissioned Officer"),
    ("SWO", "Senior Warrant Officer", "Junior Commissioned Officer"),
    ("WO", "Warrant Officer", "Junior Commissioned Officer"),
    ("BN_RSM", "Battalion/Regiment Sergeant Major", "NCO / Soldier"),
    ("BN_RQMS", "Battalion/Regiment Quarter Master Sergeant", "NCO / Soldier"),
    ("COY_BSM", "Company/Battery Sergeant Major", "NCO / Soldier"),
    ("COY_BQMS", "Company/Battery Quarter Master Sergeant", "NCO / Soldier"),
    ("SGT", "Sergeant", "NCO / Soldier"),
    ("CPL", "Corporal", "NCO / Soldier"),
    ("LCPL", "Lance Corporal", "NCO / Soldier"),
    ("SNK", "Sainik", "NCO / Soldier"),
]

DEFAULT_SETTINGS = {
    "token_prefix": ("A", "Daily token prefix"),
    "token_paper_width_mm": (80, "Thermal token paper width"),
    "token_paper_height_mm": (110, "Thermal token paper height"),
    "token_printer_name": ("", "Operating-system printer queue"),
    "token_auto_print": (False, "Send generated tokens to the configured server printer"),
    "form_printer_name": ("", "Operating-system A4 form printer queue"),
    "form_auto_print": (False, "Send generated anaesthesia forms to the configured server printer"),
    "barcode_format": ("code128", "Token barcode format"),
    "current_slide_seconds": (10, "Duration of the current OT slide"),
    "upcoming_slide_seconds": (15, "Duration of the upcoming list slide"),
    "ot_tables": (["OT-1", "OT-2", "OT-3"], "Available operation tables"),
}


def seed(db: Session) -> dict[str, str]:
    for order, (code, label, category) in enumerate(RANKS, 1):
        if not db.scalar(select(Rank).where(Rank.code == code)):
            db.add(Rank(code=code, label=label, category=category, sort_order=order))
    for key, (value, description) in DEFAULT_SETTINGS.items():
        if not db.get(AppSetting, key):
            db.add(AppSetting(key=key, value=value, description=description))

    created: dict[str, str] = {}
    user_specs = [
        ("admin", "System Administrator", "admin"),
        ("reception", "Anaesthesia Reception", "reception"),
        ("doctor", "Anaesthesia Doctor", "doctor"),
        ("ot_control", "OT Control Desk", "ot_controller"),
        ("display", "Display Screen", "display"),
    ]
    shared_password = os.getenv("CMH_ANESTHESIA_SEED_USER_PASSWORD")
    for username, display_name, role in user_specs:
        if db.scalar(select(User).where(User.username == username)):
            continue
        password = os.getenv("CMH_ANESTHESIA_ADMIN_PASSWORD") if role == "admin" else shared_password
        password = password or secrets.token_urlsafe(12)
        db.add(User(username=username, display_name=display_name, role=role, password_hash=hash_password(password)))
        created[username] = password
    db.commit()
    return created


if __name__ == "__main__":
    from .database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        credentials = seed(session)
    for name, password in credentials.items():
        print(f"{name}: {password}")
