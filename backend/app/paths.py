"""Katalog danych użytkownika — tam trafia baza SQLite wersji binarnej.

Plik wykonywalny może leżeć w katalogu tylko do odczytu (Program Files, pendrive,
folder Pobrane z blokadą zapisu), więc baza nie może powstawać obok niego.
Używamy standardowych lokalizacji systemowych:

* Windows — ``%LOCALAPPDATA%\\NauczKube``
* macOS   — ``~/Library/Application Support/NauczKube``
* Linux   — ``$XDG_DATA_HOME/NauczKube`` lub ``~/.local/share/NauczKube``

Ścieżki z polskimi znakami i spacjami muszą działać — pilnuje tego
``tests/test_paths.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "NauczKube"
DB_FILENAME = "naucz_kube.db"


def _platform_base() -> Path:
    """Bazowy katalog danych aplikacji dla bieżącego systemu."""
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) if local else Path.home() / "AppData" / "Local"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"

    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) if xdg else Path.home() / ".local" / "share"


def user_data_dir(create: bool = True) -> Path:
    """Katalog na dane aplikacji; tworzy go, jeśli nie istnieje."""
    directory = _platform_base() / APP_DIR_NAME
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def user_database_url(create: bool = True) -> str:
    """Adres SQLite do bazy w katalogu danych użytkownika.

    Ścieżkę wstawiamy dosłownie — dialekt SQLite traktuje wszystko po
    ``sqlite:///`` jak nazwę pliku, więc spacje i polskie znaki są w porządku.
    Kodowanie procentowe by to zepsuło (powstałby plik o nazwie z ``%20``).
    """
    path = user_data_dir(create=create) / DB_FILENAME
    return f"sqlite:///{path}"
