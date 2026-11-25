"""Endpointy sesji z Kubą."""

from __future__ import annotations

import random
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session as DbSession
from sqlmodel import select

from app.ai import ocr, stt
from app.api.deps import get_db, get_learning_session, rate_limit
from app.catalog import load_catalog, topics
from app.models import Session as LearningSession
from app.models import Student
from app.schemas import (
    CorrectionConfirm,
    ExplainRequest,
    MarkRequest,
    SessionCreate,
    TransferRequest,
)
from app.session import orchestrator

router = APIRouter(prefix="/api", tags=["sesje"])

MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 4 * 1024 * 1024


@router.get("/topics")
def list_topics() -> dict[str, Any]:
    return {"topics": topics()}


@router.post("/sessions", status_code=201)
def create_session(payload: SessionCreate, db: DbSession = Depends(get_db)) -> dict[str, Any]:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono ucznia.")
    rate_limit(f"student:{student.id}")

    catalog = load_catalog()
    misconception_id = payload.misconception_id
    if misconception_id is None:
        candidates = [m.id for m in catalog.values() if payload.topic in (None, m.topic)]
        if not candidates:
            raise HTTPException(status_code=404, detail="Brak błędów dla tego tematu.")
        misconception_id = _pick_weakest(db, student.id, candidates)
    if misconception_id not in catalog:
        raise HTTPException(status_code=404, detail="Nieznany błąd w katalogu.")

    session, view = orchestrator.start_session(db, student.id, misconception_id)
    return {"session": orchestrator.session_payload(session), "turn": view.as_dict()}


def _pick_weakest(db: DbSession, student_id: str, candidates: list[str]) -> str:
    """Wybiera błąd z najniższym P(L) — najpierw to, czego uczeń nie ogarnia."""
    from app.knowledge.mastery import student_map

    scores = {
        entry["misconception_id"]: entry["p_known"]
        for entry in student_map(db, student_id)["entries"]
    }
    return min(sorted(candidates), key=lambda key: scores.get(key, 0.3))


@router.get("/sessions/{session_id}")
def read_session(
    session: Annotated[LearningSession, Depends(get_learning_session)],
) -> dict[str, Any]:
    return orchestrator.session_payload(session)


@router.post("/sessions/{session_id}/mark")
def mark_line(
    payload: MarkRequest,
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    lines = orchestrator.session_lines(session)
    if payload.line_index >= len(lines):
        raise HTTPException(status_code=422, detail="Taka linijka nie istnieje.")
    return orchestrator.handle_mark(db, session, payload.line_index).as_dict()


@router.post("/sessions/{session_id}/explain")
def explain(
    payload: ExplainRequest,
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return orchestrator.handle_explanation(
        db, session, payload.text, modality=payload.modality
    ).as_dict()


@router.post("/sessions/{session_id}/explain-audio")
def explain_audio(
    session: Annotated[LearningSession, Depends(get_learning_session)],
    audio: Annotated[UploadFile, File(description="Nagranie wyjaśnienia")],
    autosend: Annotated[bool, Form()] = False,
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Nagranie → transkrypcja. Nagranie nie jest zapisywane.

    Domyślnie zwracamy samą transkrypcję do potwierdzenia przez ucznia
    (`autosend=false`), bo polska transkrypcja bywa niedokładna.
    """
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Nagranie jest za duże (maks. 8 MB).")
    transcription = stt.transcribe(data, filename=audio.filename or "nagranie.webm")
    del data  # audio nie jest nigdzie zapisywane

    if not transcription.text:
        return {
            "transcription": transcription.as_dict(),
            "turn": None,
            "message": "Nie udało się rozpoznać mowy. Wpisz wyjaśnienie z klawiatury.",
        }
    if not autosend:
        return {
            "transcription": transcription.as_dict(),
            "turn": None,
            "message": "Sprawdź transkrypcję i wyślij.",
        }
    turn = orchestrator.handle_explanation(db, session, transcription.text, modality="voice")
    return {"transcription": transcription.as_dict(), "turn": turn.as_dict()}


@router.post("/sessions/{session_id}/correction")
def correction(
    session: Annotated[LearningSession, Depends(get_learning_session)],
    image: Annotated[UploadFile, File(description="Wycinek tablicy z poprawką")],
) -> dict[str, Any]:
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Obraz jest za duży (maks. 4 MB).")
    result = ocr.recognize(data, mime=image.content_type or "image/png")
    return {"ocr": result.as_dict()}


@router.post("/sessions/{session_id}/correction/confirm")
def correction_confirm(
    payload: CorrectionConfirm,
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Uczeń potwierdza odczyt — SymPy sprawdza równoważność z poprawnym krokiem."""
    return {"verification": orchestrator.handle_correction_text(db, session, payload.latex)}


@router.post("/sessions/{session_id}/transfer")
def transfer(
    payload: TransferRequest,
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return orchestrator.handle_transfer(
        db, session, payload.approve, payload.line_index
    ).as_dict()


@router.post("/sessions/{session_id}/hint")
def hint(
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return orchestrator.request_hint(db, session).as_dict()


@router.get("/sessions/{session_id}/summary")
def summary(
    session: Annotated[LearningSession, Depends(get_learning_session)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    return orchestrator.build_summary(db, session)


@router.get("/students/{student_id}/map")
def student_map(student_id: str, db: DbSession = Depends(get_db)) -> dict[str, Any]:
    from app.knowledge.mastery import student_map as build_map

    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono ucznia.")
    data = build_map(db, student_id)
    data["pseudonym"] = student.pseudonym
    sessions = db.exec(
        select(LearningSession).where(LearningSession.student_id == student_id)
    ).all()
    data["sessions_finished"] = sum(1 for s in sessions if s.state == "DONE")
    return data


@router.post("/debug/seed-random")
def seed_random(seed: int) -> dict[str, Any]:
    """Ustala ziarno losowości (ułatwia nagranie filmu i testy E2E)."""
    random.seed(seed)
    return {"seed": seed}
