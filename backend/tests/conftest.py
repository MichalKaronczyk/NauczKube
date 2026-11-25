from __future__ import annotations

import os
import random
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OFFLINE_ONLY", "false")
# testy jednostkowe nie wysyłają nic do zewnętrznych API
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("MISTRAL_API_KEY", None)
os.environ.pop("OPENROUTER_API_KEY", None)


@pytest.fixture(scope="session", autouse=True)
def _isolate_providers() -> Iterator[None]:
    """Blokuje łańcuch providerów, żeby testy nie zużywały dziennych limitów."""
    from app.llm import providers

    original = providers.chain_for
    providers.chain_for = lambda task: []  # type: ignore[assignment]
    yield
    providers.chain_for = original  # type: ignore[assignment]


@pytest.fixture
def db(tmp_path: Path) -> Iterator[object]:
    from sqlmodel import Session, SQLModel, create_engine

    import app.db as app_db

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    original = app_db.engine
    app_db.engine = engine
    with Session(engine) as session:
        yield session
    app_db.engine = original


@pytest.fixture
def student(db):
    from app.models import Student

    row = Student(pseudonym="Ola")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def rng() -> random.Random:
    return random.Random(2026)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[object]:
    from fastapi.testclient import TestClient
    from sqlmodel import SQLModel, create_engine

    import app.db as app_db
    from app.api import deps
    from app.main import app

    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    original = app_db.engine
    app_db.engine = engine
    deps.reset_rate_limits()

    with TestClient(app) as test_client:
        yield test_client

    app_db.engine = original
