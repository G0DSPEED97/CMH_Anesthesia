from __future__ import annotations

from datetime import date, timedelta

from conftest import login
from fastapi.testclient import TestClient


def patient_payload(number: str = "BA-10001") -> dict:
    return {
        "patient": {
            "service_number": number,
            "rank_code": "MAJ",
            "name": "Test Patient",
            "unit": "10 BIR",
            "age": 41,
            "sex": "male",
        },
        "proposed_surgery": "Test operation",
        "proposed_anesthetic": "GA",
        "auto_print_token": False,
    }


def test_reception_to_ot_workflow(client: TestClient):
    login(client, "reception")
    created = client.post("/api/v1/cases", json=patient_payload())
    assert created.status_code == 201, created.text
    case = created.json()
    assert case["token_number"] == "A-001"

    token = client.get(f"/api/v1/cases/{case['id']}/token.pdf")
    form = client.get(f"/api/v1/cases/{case['id']}/form.pdf")
    assert token.status_code == 200 and token.content.startswith(b"%PDF")
    assert form.status_code == 200 and form.content.startswith(b"%PDF")

    client.post("/api/v1/auth/logout")
    login(client, "doctor")
    ot_day = (date.today() + timedelta(days=2)).isoformat()
    reviewed = client.patch(
        f"/api/v1/cases/{case['id']}/consultation",
        json={
            "status": "completed",
            "scheduled_ot_date": ot_day,
            "ward": "Surgical Ward",
            "disease": "Test diagnosis",
            "operation": "Definitive operation",
            "surgeon": "Brig Gen Surgeon",
            "anesthesiologist": "Col Anaesthesiologist",
            "asa_class": "II",
            "ot_table": "OT-1",
            "expected_version": case["version"],
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    scheduled = reviewed.json()
    assert scheduled["scheduled_ot_date"] == ot_day
    assert scheduled["ot_serial"] == 1

    client.post("/api/v1/auth/logout")
    login(client, "ot_control")
    roster = client.get("/api/v1/cases", params={"scheduled_ot_date": ot_day})
    assert roster.status_code == 200 and len(roster.json()) == 1
    updated = client.patch(
        f"/api/v1/cases/{case['id']}/ot-status",
        json={"status": "in_progress", "status_note": "Procedure underway", "ot_table": "OT-1", "expected_version": scheduled["version"]},
    )
    assert updated.status_code == 200, updated.text
    display = client.get("/api/v1/display/ot", params={"for_date": ot_day})
    assert display.status_code == 200
    assert display.json()["active"][0]["status_note"] == "Procedure underway"


def test_unique_patient_can_have_multiple_cases(client: TestClient):
    login(client, "reception")
    first = client.post("/api/v1/cases", json=patient_payload()).json()
    second_payload = patient_payload()
    second_payload["proposed_surgery"] = "Follow-up operation"
    second = client.post("/api/v1/cases", json=second_payload)
    assert second.status_code == 201, second.text
    assert second.json()["patient"]["id"] == first["patient"]["id"]
    assert second.json()["token_number"] == "A-002"


def test_role_and_version_protection(client: TestClient):
    login(client, "reception")
    case = client.post("/api/v1/cases", json=patient_payload()).json()
    denied = client.patch(
        f"/api/v1/cases/{case['id']}/consultation",
        json={"status": "called", "expected_version": case["version"]},
    )
    assert denied.status_code == 403
    client.post("/api/v1/auth/logout")
    login(client, "doctor")
    stale = client.patch(
        f"/api/v1/cases/{case['id']}/consultation",
        json={"status": "called", "expected_version": 999},
    )
    assert stale.status_code == 409
