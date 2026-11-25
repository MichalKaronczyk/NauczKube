"""Stan aplikacji: katalog, providerzy AI, limity."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlmodel import Session as DbSession
from sqlmodel import func, select

from app import __version__
from app.catalog import load_catalog
from app.config import settings
from app.llm.gateway import gateway
from app.math.verify import selfcheck_catalog
from app.models import LlmCall

router = APIRouter(prefix="/api", tags=["stan"])


@router.get("/health")
def health() -> dict[str, Any]:
    results = selfcheck_catalog()
    failed = [r.as_dict() for r in results if not r.ok]
    return {
        "status": "ok" if not failed else "degraded",
        "app": settings.app_name,
        "version": __version__,
        "catalog_items": len(load_catalog()),
        "catalog_selfcheck": {
            "checked": len(results),
            "failed": len(failed),
            "details": failed[:5],
        },
        "llm": gateway.health(),
        "latency": _latency_stats(),
    }


def _latency_stats() -> dict[str, Any]:
    """p95 opóźnień z tabeli llm_calls — liczba, którą pokazujemy jury."""
    import app.db as app_db

    try:
        with DbSession(app_db.engine) as db:
            rows = db.exec(
                select(LlmCall.task, LlmCall.latency_ms).where(
                    LlmCall.status.in_(["ok", "repaired"])
                )
            ).all()
            total = db.exec(select(func.count()).select_from(LlmCall)).one()
    except Exception:  # noqa: BLE001  # monitoring nie może wywrócić /health
        return {"calls_logged": 0, "tasks": {}}

    by_task: dict[str, list[int]] = {}
    for task, latency in rows:
        by_task.setdefault(task, []).append(latency)

    out: dict[str, Any] = {"calls_logged": total, "tasks": {}}
    for task, values in by_task.items():
        values.sort()
        index = max(0, int(round(0.95 * (len(values) - 1))))
        out["tasks"][task] = {
            "count": len(values),
            "p50_ms": values[len(values) // 2],
            "p95_ms": values[index],
        }
    return out
