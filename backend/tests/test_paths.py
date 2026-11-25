"""Katalog danych użytkownika — także na ścieżkach z polskimi znakami i spacjami."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlmodel import Field, SQLModel, create_engine, select
from sqlmodel import Session as DbSession

from app import paths

# Ścieżka, która łamie naiwne sklejanie URL-i: spacje i znaki spoza ASCII.
TRICKY = "Dokumenty Oli/Ścieżka z polskimi znakami ąćęłńóśźż"


class _Probe(SQLModel, table=True):
    """Minimalna tabela do sprawdzenia, że da się pisać do bazy."""

    __tablename__ = "probe_paths"
    id: int | None = Field(default=None, primary_key=True)
    label: str


@pytest.fixture
def tricky_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / TRICKY
    home.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData" / "Local"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    return home


def test_katalog_powstaje_i_lezy_pod_home(tricky_home: Path) -> None:
    directory = paths.user_data_dir()

    assert directory.is_dir()
    assert directory.name == paths.APP_DIR_NAME
    assert str(tricky_home) in str(directory)


def test_katalog_jest_tworzony_rekurencyjnie(tricky_home: Path) -> None:
    # Katalog bazowy jeszcze nie istnieje — funkcja musi go dociągnąć.
    assert paths.user_data_dir().is_dir()
    # Drugie wywołanie nie może wysypać się na istniejącym katalogu.
    assert paths.user_data_dir().is_dir()


def test_mozna_zalozyc_baze_na_sciezce_ze_spacjami_i_ogonkami(tricky_home: Path) -> None:
    url = paths.user_database_url()
    engine = create_engine(url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine, tables=[_Probe.__table__])

    with DbSession(engine) as db:
        db.add(_Probe(label="Zażółć gęślą jaźń"))
        db.commit()

    with DbSession(engine) as db:
        assert db.exec(select(_Probe)).one().label == "Zażółć gęślą jaźń"

    engine.dispose()
    assert (paths.user_data_dir() / paths.DB_FILENAME).exists()


@pytest.mark.skipif(sys.platform != "darwin", reason="lokalizacja zależna od systemu")
def test_macos_uzywa_application_support(tricky_home: Path) -> None:
    assert paths.user_data_dir().parent.name == "Application Support"


@pytest.mark.skipif(sys.platform != "win32", reason="lokalizacja zależna od systemu")
def test_windows_uzywa_localappdata(tricky_home: Path) -> None:
    assert "AppData" in str(paths.user_data_dir())


@pytest.mark.skipif(sys.platform == "win32", reason="lokalizacja zależna od systemu")
@pytest.mark.skipif(sys.platform == "darwin", reason="lokalizacja zależna od systemu")
def test_linux_uzywa_xdg_data_home(tricky_home: Path) -> None:
    assert ".local/share" in str(paths.user_data_dir()).replace("\\", "/")
