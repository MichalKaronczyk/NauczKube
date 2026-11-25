"""Naucz Kubę — aplikacja FastAPI.

Serwuje API pod /api oraz zbudowany frontend (jeśli jest w backend/static).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import routes_classes, routes_health, routes_sessions
from app.catalog import load_catalog
from app.config import STATIC_DIR, settings
from app.db import init_db, purge_old_solo_sessions
from app.math.verify import selfcheck_catalog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("naucz-kube")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    catalog = load_catalog()
    results = selfcheck_catalog()
    failed = [r for r in results if not r.ok]
    logger.info(
        "Katalog: %d pozycji, %d sprawdzeń SymPy, %d niepoprawnych",
        len(catalog),
        len(results),
        len(failed),
    )
    for verdict in failed:
        logger.error("Pozycja katalogu nie przechodzi autotestu: %s", verdict.as_dict())
    removed = purge_old_solo_sessions()
    if removed:
        logger.info("Retencja: usunięto %d sesji w trybie solo", removed)
    yield


app = FastAPI(
    title="Naucz Kubę",
    description=(
        "Uczeń uczy AI, a nie odwrotnie. Kuba rozwiązuje zadanie z jednym typowym "
        "błędem w rozumowaniu; uczeń musi go znaleźć i wytłumaczyć."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Teacher-Pin"],
)

app.include_router(routes_health.router)
app.include_router(routes_classes.router)
app.include_router(routes_sessions.router)


@app.get("/api/info")
def info() -> dict[str, object]:
    return {
        "app": settings.app_name,
        "version": __version__,
        "offline_only": settings.offline_only,
        "disclaimer": (
            "Kuba to program AI. Myli się celowo, żebyś mógł go nauczyć — "
            "ale czasem może pomylić się też przypadkiem."
        ),
        "privacy": (
            "Nie zbieramy danych osobowych: brak kont, e-maili i nazwisk. "
            "Nagrania głosu nie są zapisywane."
        ),
    }


# --- frontend (produkcja) --------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Nie znaleziono."}, status_code=404)
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend nie został zbudowany."}, status_code=404)

else:  # pragma: no cover

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "api": "/docs",
            "info": "Frontend uruchom osobno: cd frontend && npm run dev",
        }


def run() -> None:  # pragma: no cover - punkt wejścia dla PyInstallera
    import os
    import threading
    import webbrowser

    import uvicorn

    url = f"http://127.0.0.1:{settings.port}"
    # NAUCZ_KUBE_NO_BROWSER=1 wyłącza otwieranie przeglądarki (CI, serwer zdalny).
    no_browser = os.environ.get("NAUCZ_KUBE_NO_BROWSER", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if Path(STATIC_DIR).exists() and not no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=settings.port, log_level="info")


if __name__ == "__main__":  # pragma: no cover
    run()
