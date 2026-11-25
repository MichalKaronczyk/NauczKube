"""Zależności FastAPI: baza, limit zapytań, uwierzytelnienie nauczyciela."""

from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session as DbSession
from sqlmodel import select

from app.config import settings
from app.db import get_session
from app.models import Class
from app.models import Session as LearningSession

_lock = threading.Lock()
_requests: dict[str, deque[float]] = defaultdict(deque)

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bez znaków łatwych do pomylenia


def generate_class_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(6))


def rate_limit(key: str) -> None:
    """Limit zapytań na sesję (domyślnie 30 na 10 minut)."""
    now = time.monotonic()
    window = settings.session_rate_window_s
    with _lock:
        bucket = _requests[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= settings.session_rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Za dużo zapytań w tej sesji. Odczekaj chwilę.",
            )
        bucket.append(now)


def reset_rate_limits() -> None:
    with _lock:
        _requests.clear()


def get_db() -> DbSession:  # pragma: no cover - cienki wrapper
    yield from get_session()


def get_learning_session(
    session_id: str, db: DbSession = Depends(get_db)
) -> LearningSession:
    session = db.get(LearningSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono sesji.")
    rate_limit(session_id)
    return session


def verify_teacher(
    code: str,
    x_teacher_pin: str | None = Header(default=None, alias="X-Teacher-Pin"),
    pin: str | None = None,
    db: DbSession = Depends(get_db),
) -> Class:
    from app.api.security import verify_pin

    provided = x_teacher_pin or pin
    klass = db.exec(select(Class).where(Class.code == code.upper())).first()
    if klass is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono klasy o tym kodzie.")
    if not provided or not verify_pin(provided, klass.teacher_pin_hash):
        raise HTTPException(status_code=401, detail="Niepoprawny PIN nauczyciela.")
    return klass
