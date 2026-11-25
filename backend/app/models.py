"""Model danych (SQLite + SQLModel). 7 tabel, zero danych osobowych.

Celowo nie ma tu pól na imię, nazwisko, e-mail ani wiek. Katalog błędów nie jest
w bazie — to pliki JSON wersjonowane razem z kodem.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Class(SQLModel, table=True):
    __tablename__ = "classes"

    id: str = Field(default_factory=_uuid, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=6)
    name: str = ""
    teacher_pin_hash: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: str = Field(default_factory=_uuid, primary_key=True)
    class_id: str | None = Field(default=None, index=True)
    pseudonym: str = Field(max_length=32)
    created_at: datetime = Field(default_factory=utcnow)


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    student_id: str = Field(index=True)
    misconception_id: str = Field(index=True)
    task_params: str = "{}"          # JSON
    lines_json: str = "[]"           # JSON: wyrenderowane linijki Kuby
    state: str = "INTRO"             # stan maszyny stanów
    hints_used: int = 0
    wrong_marks: int = 0
    covered_ideas: str = "[]"        # JSON: lista id zaliczonych idei
    transfer_json: str = "{}"        # JSON: zadanie transferowe
    outcome: str | None = None       # mastered | partial | abandoned
    started_at: datetime = Field(default_factory=utcnow)
    last_activity_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class Turn(SQLModel, table=True):
    __tablename__ = "turns"

    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(index=True)
    role: str                        # student | kuba | hint | system
    modality: str = "text"           # text | voice | ink | mark
    text: str = ""
    latex: str | None = None
    emotion: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Evaluation(SQLModel, table=True):
    __tablename__ = "evaluations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    turn_id: str = Field(index=True)
    session_id: str = Field(index=True)
    ideas_json: str = "[]"
    student_errors_json: str = "[]"
    rejected_json: str = "[]"        # idee odrzucone przez walidację dowodów
    accepted: bool = False
    model_used: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Mastery(SQLModel, table=True):
    __tablename__ = "mastery"

    id: str = Field(default_factory=_uuid, primary_key=True)
    student_id: str = Field(index=True)
    misconception_id: str = Field(index=True)
    p_known: float = 0.30
    observations: int = 0
    updated_at: datetime = Field(default_factory=utcnow)


class LlmCall(SQLModel, table=True):
    __tablename__ = "llm_calls"

    id: str = Field(default_factory=_uuid, primary_key=True)
    task: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    status: str = "ok"               # ok | error | rate_limited | fallback
    created_at: datetime = Field(default_factory=utcnow)
