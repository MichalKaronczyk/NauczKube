"""Endpointy uczniów i klas + panel nauczyciela."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session as DbSession
from sqlmodel import select

from app.api.deps import generate_class_code, get_db, verify_teacher
from app.api.security import hash_pin
from app.knowledge.mastery import class_heatmap, heatmap_csv
from app.models import Class, Evaluation, Mastery, Student, Turn
from app.models import Session as LearningSession
from app.schemas import ClassCreate, ClassOut, StudentCreate, StudentOut

router = APIRouter(prefix="/api", tags=["klasy"])


@router.post("/students", status_code=201, response_model=StudentOut)
def create_student(payload: StudentCreate, db: DbSession = Depends(get_db)) -> StudentOut:
    class_id: str | None = None
    class_code: str | None = None
    if payload.class_code:
        klass = db.exec(select(Class).where(Class.code == payload.class_code)).first()
        if klass is None:
            raise HTTPException(status_code=404, detail="Nie ma klasy o takim kodzie.")
        class_id = klass.id
        class_code = klass.code

    student = Student(pseudonym=payload.pseudonym, class_id=class_id)
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentOut(
        student_id=student.id,
        pseudonym=student.pseudonym,
        class_id=class_id,
        class_code=class_code,
    )


@router.post("/classes", status_code=201, response_model=ClassOut)
def create_class(payload: ClassCreate, db: DbSession = Depends(get_db)) -> ClassOut:
    code = generate_class_code()
    while db.exec(select(Class).where(Class.code == code)).first() is not None:  # pragma: no cover
        code = generate_class_code()
    klass = Class(code=code, name=payload.name.strip(), teacher_pin_hash=hash_pin(payload.pin))
    db.add(klass)
    db.commit()
    db.refresh(klass)
    return ClassOut(class_id=klass.id, code=klass.code, name=klass.name)


@router.get("/classes/{code}/dashboard")
def dashboard(
    klass: Annotated[Class, Depends(verify_teacher)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Mapa ciepła uczniowie × błędy. Nauczyciel nie widzi treści rozmów."""
    data = class_heatmap(db, klass.id)
    data["class"] = {"code": klass.code, "name": klass.name}
    return data


@router.get("/classes/{code}/export.csv")
def export_csv(
    klass: Annotated[Class, Depends(verify_teacher)],
    db: DbSession = Depends(get_db),
) -> Response:
    csv = heatmap_csv(class_heatmap(db, klass.id))
    return Response(
        content=csv.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="klasa-{klass.code}.csv"'},
    )


@router.delete("/classes/{code}")
def delete_class(
    klass: Annotated[Class, Depends(verify_teacher)],
    db: DbSession = Depends(get_db),
) -> dict[str, Any]:
    """Usuwa klasę razem ze wszystkimi danymi uczniów (jeden przycisk)."""
    students = db.exec(select(Student).where(Student.class_id == klass.id)).all()
    removed = {"students": 0, "sessions": 0, "turns": 0, "evaluations": 0, "mastery": 0}

    for student in students:
        sessions = db.exec(
            select(LearningSession).where(LearningSession.student_id == student.id)
        ).all()
        for session in sessions:
            for turn in db.exec(select(Turn).where(Turn.session_id == session.id)).all():
                db.delete(turn)
                removed["turns"] += 1
            for evaluation in db.exec(
                select(Evaluation).where(Evaluation.session_id == session.id)
            ).all():
                db.delete(evaluation)
                removed["evaluations"] += 1
            db.delete(session)
            removed["sessions"] += 1
        for mastery in db.exec(select(Mastery).where(Mastery.student_id == student.id)).all():
            db.delete(mastery)
            removed["mastery"] += 1
        db.delete(student)
        removed["students"] += 1

    db.delete(klass)
    db.commit()
    return {"deleted": True, "removed": removed}
