from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["admin", "reception", "doctor", "ot_controller", "auditor", "display"]
ConsultationStatus = Literal["waiting", "called", "in_progress", "completed", "cancelled"]
OtStatus = Literal["waiting", "called", "in_ot", "in_progress", "completed", "cancelled"]


class LoginInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    display_name: str
    role: Role
    must_change_password: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[a-zA-Z0-9_.-]{3,80}$")
    display_name: str = Field(min_length=2, max_length=120)
    role: Role
    temporary_password: str = Field(min_length=10, max_length=200)


class RankRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    label: str
    category: str
    sort_order: int


class PatientInput(BaseModel):
    service_number: str = Field(min_length=2, max_length=40)
    rank_code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    unit: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=120)
    sex: Literal["male", "female", "other"]

    @field_validator("service_number", "name", "unit", "rank_code")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class CaseCreate(BaseModel):
    patient: PatientInput
    proposed_surgery: str = Field(min_length=2, max_length=240)
    proposed_anesthetic: str = Field(min_length=1, max_length=80)
    auto_print_token: bool = True


class PatientRead(BaseModel):
    id: str
    service_number: str
    rank_code: str
    rank_label: str
    name: str
    unit: str
    age: int
    sex: str


class CaseRead(BaseModel):
    id: str
    patient: PatientRead
    token_date: date
    token_number: str
    proposed_surgery: str
    proposed_anesthetic: str
    consultation_status: str
    scheduled_ot_date: date | None
    ot_serial: int | None
    ot_table: str | None
    ward: str | None
    disease: str | None
    operation: str | None
    surgeon: str | None
    anesthesiologist: str | None
    asa_class: str | None
    ot_status: str
    status_note: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ConsultationUpdate(BaseModel):
    status: ConsultationStatus | None = None
    scheduled_ot_date: date | None = None
    ward: str | None = Field(default=None, max_length=80)
    disease: str | None = Field(default=None, max_length=1000)
    operation: str | None = Field(default=None, max_length=240)
    surgeon: str | None = Field(default=None, max_length=160)
    anesthesiologist: str | None = Field(default=None, max_length=160)
    asa_class: Literal["I", "II", "III", "IV", "V", "E"] | None = None
    ot_table: str | None = Field(default=None, max_length=30)
    ot_serial: int | None = Field(default=None, ge=1, le=500)
    expected_version: int


class OtUpdate(BaseModel):
    status: OtStatus
    status_note: str | None = Field(default=None, max_length=240)
    ot_table: str | None = Field(default=None, max_length=30)
    expected_version: int


class SettingUpdate(BaseModel):
    token_prefix: str = Field(pattern=r"^[A-Z0-9-]{1,8}$")
    token_paper_width_mm: int = Field(ge=48, le=112)
    token_paper_height_mm: int = Field(ge=60, le=200)
    token_printer_name: str = Field(max_length=160)
    token_auto_print: bool
    form_printer_name: str = Field(max_length=160)
    form_auto_print: bool
    barcode_format: Literal["code128"] = "code128"
    current_slide_seconds: int = Field(ge=5, le=60)
    upcoming_slide_seconds: int = Field(ge=5, le=60)
    ot_tables: list[str] = Field(min_length=1, max_length=30)


class PrintResult(BaseModel):
    generated: bool
    queued: bool
    message: str
