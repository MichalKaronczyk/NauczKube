"""Połączenie z bazą SQLite."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

from sqlmodel import Session as DbSession
from sqlmodel import SQLModel, create_engine, select

from app.config import settings
from app.models import Session as LearningSession
from app.models import Turn, utcnow

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[DbSession]:
    with DbSession(engine) as session:
        yield session


def purge_old_solo_sessions() -> int:
    """Retencja: sesje w trybie solo starsze niż N dni są usuwane."""
    cutoff = utcnow() - timedelta(days=settings.solo_retention_days)
    removed = 0
    with DbSession(engine) as db:
        from app.models import Student

        solo_ids = {
            s.id for s in db.exec(select(Student).where(Student.class_id.is_(None))).all()
        }
        if not solo_ids:
            return 0
        old = db.exec(
            select(LearningSession).where(LearningSession.started_at < cutoff)
        ).all()
        for sess in old:
            if sess.student_id not in solo_ids:
                continue
            for turn in db.exec(select(Turn).where(Turn.session_id == sess.id)).all():
                db.delete(turn)
            db.delete(sess)
            removed += 1
        db.commit()
    return removed
