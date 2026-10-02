from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    COOKIE_SECURE,
    DUMMY_HASH,
    SESSION_COOKIE,
    current_user,
    hash_password,
    issue_session,
    require_roles,
    session_user,
    verify_password,
)
from .database import Base, SessionLocal, engine, get_db
from .documents import create_anesthesia_form_pdf, create_token_pdf, queue_form_print, queue_token_print
from .models import AnesthesiaCase, AppSetting, AuditLog, DailyCounter, Patient, Rank, User, UserSession
from .realtime import hub
from .schemas import (
    CaseCreate,
    CaseRead,
    ConsultationUpdate,
    LoginInput,
    OtUpdate,
    PasswordChange,
    PrintResult,
    RankRead,
    SettingUpdate,
    UserCreate,
    UserRead,
)
from .seed import seed

API = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        created = seed(db)
    if created:
        print("Initial credentials (store securely; each account must change its password):")
        for username, password in created.items():
            print(f"  {username}: {password}")
    yield


app = FastAPI(title="CMH Anaesthesia Management System", version="1.0.0", lifespan=lifespan)


def _settings(db: Session) -> dict:
    return {item.key: item.value for item in db.scalars(select(AppSetting)).all()}


def _case_read(case: AnesthesiaCase) -> dict:
    patient = case.patient
    return {
        "id": case.id,
        "patient": {
            "id": patient.id,
            "service_number": patient.service_number,
            "rank_code": patient.rank_code,
            "rank_label": patient.rank.label,
            "name": patient.name,
            "unit": patient.unit,
            "age": patient.age,
            "sex": patient.sex,
        },
        "token_date": case.token_date,
        "token_number": case.token_number,
        "proposed_surgery": case.proposed_surgery,
        "proposed_anesthetic": case.proposed_anesthetic,
        "consultation_status": case.consultation_status,
        "scheduled_ot_date": case.scheduled_ot_date,
        "ot_serial": case.ot_serial,
        "ot_table": case.ot_table,
        "ward": case.ward,
        "disease": case.disease,
        "operation": case.operation,
        "surgeon": case.surgeon,
        "anesthesiologist": case.anesthesiologist,
        "asa_class": case.asa_class,
        "ot_status": case.ot_status,
        "status_note": case.status_note,
        "version": case.version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def _audit(db: Session, actor: User, action: str, case: AnesthesiaCase, details: dict | None = None) -> None:
    db.add(AuditLog(actor=actor.username, action=action, entity_type="anesthesia_case", entity_id=case.id, details=details or {}))


def _get_case(db: Session, case_id: str) -> AnesthesiaCase:
    case = db.get(AnesthesiaCase, case_id)
    if not case:
        raise HTTPException(404, "Patient case not found")
    return case


def _ensure_version(case: AnesthesiaCase, expected: int) -> None:
    if case.version != expected:
        raise HTTPException(409, "This record changed on another computer. Refresh and try again.")


@app.get(f"{API}/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "database": "ready", "printing": "server-queue"}


@app.post(f"{API}/auth/login", response_model=UserRead)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.username) == payload.username.strip().lower()))
    valid = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if not user or not user.is_active or not valid:
        raise HTTPException(401, "Invalid username or password")
    token = issue_session(db, user)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=12 * 60 * 60,
        path="/",
    )
    return user


@app.post(f"{API}/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        session = db.get(UserSession, __import__("hashlib").sha256(raw.encode()).hexdigest())
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@app.get(f"{API}/auth/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user


@app.post(f"{API}/auth/password", status_code=204)
def change_password(payload: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()


@app.get(f"{API}/users", response_model=list[UserRead])
def users(_: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.display_name)).all()


@app.post(f"{API}/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.username) == payload.username.lower())):
        raise HTTPException(409, "Username already exists")
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        role=payload.role,
        password_hash=hash_password(payload.temporary_password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get(f"{API}/ranks", response_model=list[RankRead])
def ranks(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Rank).where(Rank.is_active.is_(True)).order_by(Rank.sort_order)).all()


@app.get(f"{API}/settings")
def get_settings(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return _settings(db)


@app.put(f"{API}/settings")
async def update_settings(payload: SettingUpdate, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    for key, value in payload.model_dump().items():
        item = db.get(AppSetting, key)
        if item:
            item.value = value
    db.add(AuditLog(actor=user.username, action="settings.update", entity_type="settings", entity_id="global", details=payload.model_dump()))
    db.commit()
    await hub.publish("settings.updated")
    return _settings(db)


@app.post(f"{API}/cases", response_model=CaseRead, status_code=201)
async def create_case(payload: CaseCreate, background: BackgroundTasks, user: User = Depends(require_roles("reception")), db: Session = Depends(get_db)):
    patient_data = payload.patient
    patient = db.scalar(select(Patient).where(func.lower(Patient.service_number) == patient_data.service_number.lower()))
    rank = db.scalar(select(Rank).where(Rank.code == patient_data.rank_code, Rank.is_active.is_(True)))
    if not rank:
        raise HTTPException(400, "Select a valid rank")
    if patient:
        patient.rank_code = patient_data.rank_code
        patient.name = patient_data.name
        patient.unit = patient_data.unit
        patient.age = patient_data.age
        patient.sex = patient_data.sex
    else:
        patient = Patient(**patient_data.model_dump())
        db.add(patient)
        db.flush()

    today = date.today()
    counter = db.scalar(select(DailyCounter).where(DailyCounter.counter_date == today).with_for_update())
    if not counter:
        counter = DailyCounter(counter_date=today, value=0)
        db.add(counter)
        db.flush()
    counter.value += 1
    settings = _settings(db)
    token = f"{settings.get('token_prefix', 'A')}-{counter.value:03d}"
    case = AnesthesiaCase(
        patient_id=patient.id,
        token_date=today,
        token_sequence=counter.value,
        token_number=token,
        proposed_surgery=payload.proposed_surgery.strip(),
        proposed_anesthetic=payload.proposed_anesthetic.strip(),
        created_by=user.id,
    )
    db.add(case)
    db.flush()
    token_path = create_token_pdf(case, settings)
    form_path = create_anesthesia_form_pdf(case)
    case.token_pdf_path = str(token_path)
    case.form_pdf_path = str(form_path)
    _audit(db, user, "case.create", case, {"token_number": token})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "The patient or token was created concurrently; retry once") from exc
    db.refresh(case)
    if payload.auto_print_token:
        background.add_task(queue_token_print, token_path, settings)
    background.add_task(queue_form_print, form_path, settings)
    await hub.publish("case.created")
    return _case_read(case)


@app.get(f"{API}/cases", response_model=list[CaseRead])
def list_cases(
    q: str = "",
    consultation_status: str | None = None,
    token_date: date | None = None,
    scheduled_ot_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(AnesthesiaCase).join(Patient)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.where(or_(Patient.name.ilike(term), Patient.service_number.ilike(term), AnesthesiaCase.token_number.ilike(term)))
    if consultation_status:
        query = query.where(AnesthesiaCase.consultation_status == consultation_status)
    if token_date:
        query = query.where(AnesthesiaCase.token_date == token_date)
    if scheduled_ot_date:
        query = query.where(AnesthesiaCase.scheduled_ot_date == scheduled_ot_date)
    cases = db.scalars(query.order_by(AnesthesiaCase.created_at.desc()).limit(limit)).unique().all()
    return [_case_read(case) for case in cases]


@app.patch(f"{API}/cases/{{case_id}}/consultation", response_model=CaseRead)
async def update_consultation(case_id: str, payload: ConsultationUpdate, user: User = Depends(require_roles("doctor")), db: Session = Depends(get_db)):
    case = _get_case(db, case_id)
    _ensure_version(case, payload.expected_version)
    changes = payload.model_dump(exclude={"expected_version"}, exclude_unset=True)
    for key, value in changes.items():
        setattr(case, key, value)
    if payload.scheduled_ot_date and not case.operation:
        case.operation = case.proposed_surgery
    if payload.scheduled_ot_date and case.ot_serial is None:
        max_serial = db.scalar(select(func.max(AnesthesiaCase.ot_serial)).where(AnesthesiaCase.scheduled_ot_date == payload.scheduled_ot_date)) or 0
        case.ot_serial = max_serial + 1
    case.version += 1
    audit_changes = payload.model_dump(mode="json", exclude={"expected_version"}, exclude_unset=True)
    _audit(db, user, "consultation.update", case, audit_changes)
    db.commit()
    db.refresh(case)
    await hub.publish("consultation.updated")
    return _case_read(case)


@app.patch(f"{API}/cases/{{case_id}}/ot-status", response_model=CaseRead)
async def update_ot_status(case_id: str, payload: OtUpdate, user: User = Depends(require_roles("ot_controller")), db: Session = Depends(get_db)):
    case = _get_case(db, case_id)
    _ensure_version(case, payload.expected_version)
    if not case.scheduled_ot_date:
        raise HTTPException(409, "A doctor must schedule an OT date before OT status can be changed")
    case.ot_status = payload.status
    case.status_note = payload.status_note
    if payload.ot_table is not None:
        case.ot_table = payload.ot_table
    case.version += 1
    _audit(db, user, "ot.status", case, payload.model_dump(exclude={"expected_version"}))
    db.commit()
    db.refresh(case)
    await hub.publish("ot.updated")
    return _case_read(case)


@app.get(f"{API}/display/reception")
def reception_display(_: User = Depends(current_user), db: Session = Depends(get_db)):
    today = date.today()
    cases = db.scalars(
        select(AnesthesiaCase)
        .where(AnesthesiaCase.token_date == today, AnesthesiaCase.consultation_status.in_(["waiting", "called", "in_progress"]))
        .order_by(AnesthesiaCase.token_sequence)
    ).unique().all()
    current = next((case for case in cases if case.consultation_status in {"called", "in_progress"}), None)
    return {"current": _case_read(current) if current else None, "upcoming": [_case_read(case) for case in cases if case.consultation_status == "waiting"][:5]}


@app.get(f"{API}/display/ot")
def ot_display(for_date: date = Query(default_factory=date.today), _: User = Depends(current_user), db: Session = Depends(get_db)):
    cases = db.scalars(
        select(AnesthesiaCase)
        .where(AnesthesiaCase.scheduled_ot_date == for_date, AnesthesiaCase.ot_status != "cancelled")
        .order_by(AnesthesiaCase.ot_serial.asc().nullslast(), AnesthesiaCase.created_at)
    ).unique().all()
    active = [case for case in cases if case.ot_status in {"in_ot", "in_progress"}]
    upcoming = [case for case in cases if case.ot_status in {"waiting", "called"}]
    completed = [case for case in cases if case.ot_status == "completed"]
    return {
        "date": for_date,
        "active": [_case_read(case) for case in active],
        "upcoming": [_case_read(case) for case in upcoming[:3]],
        "completed_count": len(completed),
        "settings": {key: _settings(db).get(key) for key in ("current_slide_seconds", "upcoming_slide_seconds")},
    }


@app.post(f"{API}/cases/{{case_id}}/print-token", response_model=PrintResult)
def print_token(case_id: str, _: User = Depends(require_roles("reception")), db: Session = Depends(get_db)):
    case = _get_case(db, case_id)
    path = Path(case.token_pdf_path or create_token_pdf(case, _settings(db)))
    queued, message = queue_token_print(path, _settings(db))
    return {"generated": True, "queued": queued, "message": message}


@app.get(f"{API}/cases/{{case_id}}/token.pdf")
def token_pdf(case_id: str, _: User = Depends(require_roles("reception", "doctor")), db: Session = Depends(get_db)):
    case = _get_case(db, case_id)
    path = Path(case.token_pdf_path or create_token_pdf(case, _settings(db)))
    return FileResponse(path, media_type="application/pdf", filename=f"{case.token_number}-token.pdf")


@app.get(f"{API}/cases/{{case_id}}/form.pdf")
def form_pdf(case_id: str, _: User = Depends(require_roles("reception", "doctor")), db: Session = Depends(get_db)):
    case = _get_case(db, case_id)
    path = Path(case.form_pdf_path or create_anesthesia_form_pdf(case))
    return FileResponse(path, media_type="application/pdf", filename=f"{case.token_number}-anaesthesia-form.pdf")


@app.websocket(f"{API}/ws")
async def websocket_endpoint(websocket: WebSocket):
    with SessionLocal() as db:
        user = session_user(db, websocket.cookies.get(SESSION_COOKIE))
    if not user:
        await websocket.close(code=4401)
        return
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "cmh-anesthesia" / "browser"
if FRONTEND_DIST.exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        requested = FRONTEND_DIST / path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
