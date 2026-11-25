"""Punkt wejścia dla wersji binarnej (PyInstaller).

Uruchamia serwer na localhost i otwiera przeglądarkę. Baza SQLite trafia do
katalogu danych użytkownika (patrz ``app/paths.py``), więc aplikacja nie wymaga
instalacji ani prawa zapisu w katalogu z plikiem wykonywalnym.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _base_dir() -> Path:
    """Katalog z zasobami — inny w paczce PyInstallera niż w repozytorium."""
    bundled = getattr(sys, "_MEIPASS", None)
    return Path(bundled) if bundled else Path(__file__).resolve().parent


def main() -> None:
    base = _base_dir()

    # PyInstaller rozpakowuje zasoby do katalogu tymczasowego
    if getattr(sys, "_MEIPASS", None):
        sys.path.insert(0, str(base))
        import app.config as config

        config.CATALOG_DIR = base / "catalog"
        config.STATIC_DIR = base / "static"

    # Baza w katalogu danych użytkownika — plik wykonywalny może leżeć
    # w miejscu tylko do odczytu (Program Files, pendrive, folder z blokadą).
    if not os.environ.get("DATABASE_URL"):
        from app.paths import user_database_url

        os.environ["DATABASE_URL"] = user_database_url()

    from app.main import run

    run()


if __name__ == "__main__":
    main()
