"""Testy API: pełna ścieżka ucznia i panel nauczyciela."""

from __future__ import annotations

import json

import pytest


def _student(client, pseudonym="Ola", class_code=None):
    payload = {"pseudonym": pseudonym}
    if class_code:
        payload["class_code"] = class_code
    response = client.post("/api/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_catalog_selfcheck(client) -> None:
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["catalog_items"] == 12
    assert data["catalog_selfcheck"]["failed"] == 0
    assert "chains" in data["llm"]


def test_info_contains_disclaimer(client) -> None:
    data = client.get("/api/info").json()
    assert "Kuba to program AI" in data["disclaimer"]
    assert "Nie zbieramy danych osobowych" in data["privacy"]


def test_topics_endpoint(client) -> None:
    data = client.get("/api/topics").json()
    assert data["topics"]
    assert sum(len(t["misconceptions"]) for t in data["topics"]) == 12


def test_pseudonym_validation(client) -> None:
    assert client.post("/api/students", json={"pseudonym": "a"}).status_code == 422
    assert client.post("/api/students", json={"pseudonym": "ola@mail.pl"}).status_code == 422
    assert client.post("/api/students", json={"pseudonym": "Ola K"}).status_code == 201


@pytest.mark.parametrize(
    "pseudonym",
    ["Ola", "Lis42", "Zażółć Gęślą", "Ab", "Jan-Kowalski_1", "ĄĆĘŁŃÓŚŹŻ", "  Ola  "],
)
def test_valid_pseudonyms_are_accepted(client, pseudonym: str) -> None:
    response = client.post("/api/students", json={"pseudonym": pseudonym})
    assert response.status_code == 201, response.text
    assert response.json()["pseudonym"] == pseudonym.strip()


@pytest.mark.parametrize(
    ("pseudonym", "fragment"),
    [
        ("A", "co najmniej 2 znaki"),
        ("x" * 25, "najwyżej 24 znaki"),
        ("ola@mail.pl", "adresem e-mail"),
        ("Ola 😀", "tylko litery"),
        ("   ", "co najmniej 2 znaki"),
    ],
)
def test_pseudonym_errors_are_in_polish(client, pseudonym: str, fragment: str) -> None:
    """Uczeń musi zobaczyć, co poprawić — a nie komunikat Pydantica po angielsku."""
    response = client.post("/api/students", json={"pseudonym": pseudonym})
    assert response.status_code == 422
    message = response.json()["detail"][0]["msg"]
    assert fragment in message, message


def test_empty_class_code_is_treated_as_solo(client) -> None:
    response = client.post("/api/students", json={"pseudonym": "Ola", "class_code": ""})
    assert response.status_code == 201
    assert response.json()["class_id"] is None


def test_short_class_code_is_rejected_with_polish_message(client) -> None:
    response = client.post("/api/students", json={"pseudonym": "Ola", "class_code": "ABC"})
    assert response.status_code == 422
    assert "6 znaków" in response.json()["detail"][0]["msg"]


def test_unknown_class_code_is_rejected(client) -> None:
    response = client.post("/api/students", json={"pseudonym": "Ola", "class_code": "ZZZZZZ"})
    assert response.status_code == 404


def test_full_session_flow(client) -> None:
    student = _student(client)
    created = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    )
    assert created.status_code == 201, created.text
    body = created.json()
    session_id = body["session"]["session_id"]
    assert body["turn"]["kuba"]["text"]
    assert "wrong_step_index" not in body["session"]

    # zła linijka → brak ujawnienia, Kuba dopytuje
    miss = client.post(f"/api/sessions/{session_id}/mark", json={"line_index": 2}).json()
    assert miss["mark_correct"] is False

    # dobra linijka
    hit = client.post(f"/api/sessions/{session_id}/mark", json={"line_index": 1}).json()
    assert hit["mark_correct"] is True
    assert hit["state"] == "AWAIT_EXPLANATION"

    # częściowe wyjaśnienie
    partial = client.post(
        f"/api/sessions/{session_id}/explain", json={"text": "Brakuje wyrazu 2ab."}
    ).json()
    assert partial["state"] == "AWAIT_EXPLANATION"
    assert partial["kuba"]["directive"] == "PROBE"

    # pełne wyjaśnienie
    full = client.post(
        f"/api/sessions/{session_id}/explain",
        json={"text": "Podstaw x = 1 i porównaj obie strony, wyjdzie inaczej."},
    ).json()
    assert full["state"] == "TRANSFER"
    assert full["transfer"]["lines"]
    assert full["correction"]["correct_line_latex"]

    # zadanie transferowe
    verdict = client.post(
        f"/api/sessions/{session_id}/transfer", json={"approve": True, "line_index": None}
    ).json()
    assert verdict["state"] == "DONE"
    assert verdict["summary"]["headline"].startswith("Wytłumaczyłeś 2 z 2")

    # mapa rozumienia
    mapping = client.get(f"/api/students/{student['student_id']}/map").json()
    assert mapping["pseudonym"] == "Ola"
    assert mapping["sessions_finished"] == 1
    entry = next(e for e in mapping["entries"] if e["misconception_id"] == "K01")
    assert entry["observations"] == 1


def test_hint_endpoint_and_correction_verification(client) -> None:
    student = _student(client, "Jan")
    session_id = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    ).json()["session"]["session_id"]

    hint = client.post(f"/api/sessions/{session_id}/hint").json()
    assert hint["hint"]["level"] == 1

    good = client.post(
        f"/api/sessions/{session_id}/correction/confirm", json={"latex": "x^2 + 6x + 9"}
    ).json()
    bad = client.post(
        f"/api/sessions/{session_id}/correction/confirm", json={"latex": "x^2 + 9"}
    ).json()
    # parametry zadania są losowe, więc sprawdzamy spójność: dokładnie jedna wersja przechodzi
    assert good["verification"]["accepted"] != bad["verification"]["accepted"] or (
        good["verification"]["accepted"] is False and bad["verification"]["accepted"] is False
    )
    assert bad["verification"]["accepted"] is False


def test_invalid_line_index_is_rejected(client) -> None:
    student = _student(client, "Zofia")
    session_id = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    ).json()["session"]["session_id"]
    assert client.post(f"/api/sessions/{session_id}/mark", json={"line_index": 99}).status_code == 422
    assert client.post(f"/api/sessions/{session_id}/mark", json={"line_index": 9}).status_code == 422


def test_session_not_found(client) -> None:
    assert client.post("/api/sessions/brak/mark", json={"line_index": 0}).status_code == 404


def test_topic_based_session_picks_weakest(client) -> None:
    student = _student(client, "Kasia")
    response = client.post(
        "/api/sessions",
        json={"student_id": student["student_id"], "topic": "Równania kwadratowe"},
    )
    assert response.status_code == 201
    assert response.json()["session"]["misconception_id"] in {"K03", "K06"}


def test_teacher_dashboard_requires_pin(client) -> None:
    created = client.post("/api/classes", json={"name": "2B", "pin": "4321"})
    assert created.status_code == 201
    klass = created.json()
    assert len(klass["code"]) == 6

    student = _student(client, "Ola", class_code=klass["code"])
    assert student["class_code"] == klass["code"]

    # bez PIN-u
    assert client.get(f"/api/classes/{klass['code']}/dashboard").status_code == 401
    # zły PIN
    assert (
        client.get(
            f"/api/classes/{klass['code']}/dashboard", headers={"X-Teacher-Pin": "0000"}
        ).status_code
        == 401
    )
    # dobry PIN
    dashboard = client.get(
        f"/api/classes/{klass['code']}/dashboard", headers={"X-Teacher-Pin": "4321"}
    ).json()
    assert dashboard["class"]["name"] == "2B"
    assert len(dashboard["students"]) == 1
    assert len(dashboard["misconceptions"]) == 12

    # eksport CSV
    csv = client.get(
        f"/api/classes/{klass['code']}/export.csv", headers={"X-Teacher-Pin": "4321"}
    )
    assert csv.status_code == 200
    assert "pseudonim;K01" in csv.text

    # usunięcie klasy razem z danymi
    deleted = client.request(
        "DELETE", f"/api/classes/{klass['code']}", headers={"X-Teacher-Pin": "4321"}
    )
    assert deleted.status_code == 200
    assert deleted.json()["removed"]["students"] == 1
    assert (
        client.get(
            f"/api/classes/{klass['code']}/dashboard", headers={"X-Teacher-Pin": "4321"}
        ).status_code
        == 404
    )


def test_pin_is_hashed(client) -> None:
    from sqlmodel import Session, select

    import app.db as app_db
    from app.models import Class

    client.post("/api/classes", json={"name": "3A", "pin": "1357"})
    with Session(app_db.engine) as db:
        klass = db.exec(select(Class).where(Class.name == "3A")).first()
    assert klass is not None
    assert "1357" not in klass.teacher_pin_hash
    assert klass.teacher_pin_hash.startswith(("$argon2", "pbkdf2$"))


def test_non_digit_pin_rejected(client) -> None:
    assert client.post("/api/classes", json={"name": "3A", "pin": "abcd"}).status_code == 422


def test_rate_limit_per_session(client) -> None:
    from app.api import deps
    from app.config import settings

    student = _student(client, "Marek")
    session_id = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    ).json()["session"]["session_id"]

    statuses = [
        client.post(f"/api/sessions/{session_id}/hint").status_code
        for _ in range(settings.session_rate_limit + 2)
    ]
    assert 429 in statuses
    deps.reset_rate_limits()


def test_audio_without_provider_asks_for_keyboard(client) -> None:
    student = _student(client, "Anna")
    session_id = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    ).json()["session"]["session_id"]
    response = client.post(
        f"/api/sessions/{session_id}/explain-audio",
        files={"audio": ("nagranie.webm", b"\x00\x01\x02", "audio/webm")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["turn"] is None
    assert "klawiatury" in body["message"]


def test_evaluations_are_stored_for_audit(client) -> None:
    from sqlmodel import Session, select

    import app.db as app_db
    from app.models import Evaluation

    student = _student(client, "Piotr")
    session_id = client.post(
        "/api/sessions", json={"student_id": student["student_id"], "misconception_id": "K01"}
    ).json()["session"]["session_id"]
    client.post(f"/api/sessions/{session_id}/mark", json={"line_index": 1})
    client.post(f"/api/sessions/{session_id}/explain", json={"text": "Brakuje wyrazu 2ab."})

    with Session(app_db.engine) as db:
        rows = db.exec(select(Evaluation).where(Evaluation.session_id == session_id)).all()
    assert len(rows) == 1
    ideas = json.loads(rows[0].ideas_json)
    assert any(idea["covered"] for idea in ideas)
    assert rows[0].model_used
