"""Mapa rozumienia ucznia i mapa ciepła klasy (dla panelu nauczyciela)."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.catalog import load_catalog
from app.config import settings
from app.knowledge.bkt import is_mastered, update
from app.models import Mastery, Student, utcnow


def get_or_create(db: DbSession, student_id: str, misconception_id: str) -> Mastery:
    row = db.exec(
        select(Mastery).where(
            Mastery.student_id == student_id,
            Mastery.misconception_id == misconception_id,
        )
    ).first()
    if row is None:
        row = Mastery(
            student_id=student_id,
            misconception_id=misconception_id,
            p_known=settings.bkt_p_init,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def record_observation(
    db: DbSession, student_id: str, misconception_id: str, correct: bool
) -> Mastery:
    row = get_or_create(db, student_id, misconception_id)
    before = row.p_known
    row.p_known = round(update(before, correct), 4)
    row.observations += 1
    row.updated_at = utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def student_map(db: DbSession, student_id: str) -> dict[str, Any]:
    catalog = load_catalog()
    rows = {
        row.misconception_id: row
        for row in db.exec(select(Mastery).where(Mastery.student_id == student_id)).all()
    }
    entries = []
    for key, item in sorted(catalog.items()):
        row = rows.get(key)
        p_known = row.p_known if row else settings.bkt_p_init
        entries.append(
            {
                "misconception_id": key,
                "title": item.title,
                "topic": item.topic,
                "p_known": round(p_known, 3),
                "observations": row.observations if row else 0,
                "mastered": is_mastered(p_known),
                "seen": row is not None,
            }
        )
    return {
        "student_id": student_id,
        "threshold": settings.bkt_mastery_threshold,
        "entries": entries,
    }


def class_heatmap(db: DbSession, class_id: str) -> dict[str, Any]:
    catalog = load_catalog()
    students = db.exec(select(Student).where(Student.class_id == class_id)).all()
    misconception_ids = sorted(catalog)

    rows: list[dict[str, Any]] = []
    for student in sorted(students, key=lambda s: s.pseudonym.lower()):
        mastery = {
            m.misconception_id: m
            for m in db.exec(select(Mastery).where(Mastery.student_id == student.id)).all()
        }
        cells = []
        for key in misconception_ids:
            row = mastery.get(key)
            p_known = row.p_known if row else None
            cells.append(
                {
                    "misconception_id": key,
                    "p_known": round(p_known, 3) if p_known is not None else None,
                    "observations": row.observations if row else 0,
                    "mastered": is_mastered(p_known) if p_known is not None else False,
                }
            )
        rows.append({"student_id": student.id, "pseudonym": student.pseudonym, "cells": cells})

    totals = []
    for index, key in enumerate(misconception_ids):
        values = [r["cells"][index]["p_known"] for r in rows if r["cells"][index]["p_known"] is not None]
        mastered = [
            1 for r in rows if r["cells"][index]["p_known"] is not None and r["cells"][index]["mastered"]
        ]
        totals.append(
            {
                "misconception_id": key,
                "title": catalog[key].title,
                "topic": catalog[key].topic,
                "students_seen": len(values),
                "students_mastered": len(mastered),
                "avg_p_known": round(sum(values) / len(values), 3) if values else None,
            }
        )

    return {
        "misconceptions": [
            {"id": key, "title": catalog[key].title, "topic": catalog[key].topic}
            for key in misconception_ids
        ],
        "students": rows,
        "summary": totals,
        "threshold": settings.bkt_mastery_threshold,
    }


def heatmap_csv(heatmap: dict[str, Any]) -> str:
    header = ["pseudonim", *[m["id"] for m in heatmap["misconceptions"]]]
    lines = [";".join(header)]
    for row in heatmap["students"]:
        values = [
            "" if cell["p_known"] is None else f"{cell['p_known']:.3f}".replace(".", ",")
            for cell in row["cells"]
        ]
        lines.append(";".join([row["pseudonym"], *values]))
    return "\n".join(lines) + "\n"
