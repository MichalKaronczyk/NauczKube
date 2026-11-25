"""Kontrakty API (Pydantic). Żadne pole nie przyjmuje danych osobowych."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PSEUDONYM = re.compile(r"^[\w \-ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,24}$")


class StudentCreate(BaseModel):
    # Walidacja długości jest w walidatorze, a nie w Field, żeby komunikat
    # dla ucznia był po polsku (Pydantic generuje domyślne po angielsku).
    pseudonym: str
    class_code: str | None = None

    @field_validator("pseudonym")
    @classmethod
    def _check(cls, value: str) -> str:
        value = value.strip()
        if "@" in value:
            raise ValueError("Pseudonim nie może być adresem e-mail.")
        if len(value) < 2:
            raise ValueError("Pseudonim musi mieć co najmniej 2 znaki.")
        if len(value) > 24:
            raise ValueError("Pseudonim może mieć najwyżej 24 znaki.")
        if not PSEUDONYM.match(value):
            raise ValueError("Pseudonim może zawierać tylko litery, cyfry, spację i myślnik.")
        return value

    @field_validator("class_code")
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        code = value.strip().upper()
        if len(code) != 6:
            raise ValueError("Kod klasy ma dokładnie 6 znaków.")
        return code


class StudentOut(BaseModel):
    student_id: str
    pseudonym: str
    class_id: str | None = None
    class_code: str | None = None


class SessionCreate(BaseModel):
    student_id: str
    misconception_id: str | None = None
    topic: str | None = None


class MarkRequest(BaseModel):
    line_index: int = Field(ge=0, le=20)


class ExplainRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    modality: Literal["text", "voice", "ink"] = "text"


class CorrectionConfirm(BaseModel):
    latex: str = Field(min_length=1, max_length=400)


class TransferRequest(BaseModel):
    approve: bool
    line_index: int | None = Field(default=None, ge=0, le=20)


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    pin: str = Field(min_length=4, max_length=12)

    @field_validator("pin")
    @classmethod
    def _digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN musi składać się z cyfr.")
        return value


class ClassOut(BaseModel):
    class_id: str
    code: str
    name: str


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    catalog_items: int
    catalog_selfcheck: dict[str, Any]
    llm: dict[str, Any]
