"""Model wiedzy (BKT) i mapa rozumienia."""

from __future__ import annotations

import pytest

from app.config import settings
from app.knowledge.bkt import (
    DEFAULT_PARAMS,
    is_mastered,
    observation_is_correct,
    posterior,
    update,
)


def test_default_parameters_match_specification() -> None:
    assert DEFAULT_PARAMS.p_init == pytest.approx(0.30)
    assert DEFAULT_PARAMS.p_transit == pytest.approx(0.20)
    assert DEFAULT_PARAMS.p_guess == pytest.approx(0.15)
    assert DEFAULT_PARAMS.p_slip == pytest.approx(0.10)
    assert DEFAULT_PARAMS.mastery_threshold == pytest.approx(0.95)


def test_posterior_formula() -> None:
    p = 0.3
    s, g = DEFAULT_PARAMS.p_slip, DEFAULT_PARAMS.p_guess
    expected = p * (1 - s) / (p * (1 - s) + (1 - p) * g)
    assert posterior(p, True) == pytest.approx(expected)


def test_correct_observation_raises_and_wrong_lowers() -> None:
    start = settings.bkt_p_init
    assert update(start, True) > start
    assert update(start, False) < start


def test_sequence_reaches_mastery() -> None:
    p = settings.bkt_p_init
    for _ in range(6):
        p = update(p, True)
    assert is_mastered(p), f"po 6 poprawnych obserwacjach P(L) = {p:.3f}"


def test_probability_stays_in_range() -> None:
    p = settings.bkt_p_init
    for correct in (True, False, True, True, False, False, True):
        p = update(p, correct)
        assert 0.0 <= p <= 1.0


def test_observation_definition() -> None:
    assert observation_is_correct(
        marked_correctly=True, explanation_complete=True, strong_hints_used=0, transfer_correct=True
    )
    # podpowiedź poziomu 2 lub 3 unieważnia obserwację
    assert not observation_is_correct(
        marked_correctly=True, explanation_complete=True, strong_hints_used=1, transfer_correct=True
    )
    assert not observation_is_correct(
        marked_correctly=False, explanation_complete=True, strong_hints_used=0, transfer_correct=True
    )
    assert not observation_is_correct(
        marked_correctly=True, explanation_complete=False, strong_hints_used=0, transfer_correct=True
    )
    assert not observation_is_correct(
        marked_correctly=True, explanation_complete=True, strong_hints_used=0, transfer_correct=False
    )


def test_student_map_lists_whole_catalog(db, student) -> None:
    from app.knowledge.mastery import record_observation, student_map

    record_observation(db, student.id, "K01", True)
    data = student_map(db, student.id)
    assert len(data["entries"]) == 12
    entry = next(e for e in data["entries"] if e["misconception_id"] == "K01")
    assert entry["observations"] == 1
    assert entry["seen"] is True
    assert entry["p_known"] > settings.bkt_p_init
    unseen = next(e for e in data["entries"] if e["misconception_id"] == "K12")
    assert unseen["seen"] is False


def test_class_heatmap_and_csv(db) -> None:
    from app.api.security import hash_pin
    from app.knowledge.mastery import class_heatmap, heatmap_csv, record_observation
    from app.models import Class, Student

    klass = Class(code="ABC234", name="2B", teacher_pin_hash=hash_pin("1234"))
    db.add(klass)
    db.commit()
    db.refresh(klass)

    for name in ("Ola", "Jan"):
        row = Student(pseudonym=name, class_id=klass.id)
        db.add(row)
        db.commit()
        db.refresh(row)
        record_observation(db, row.id, "K01", name == "Ola")

    heatmap = class_heatmap(db, klass.id)
    assert len(heatmap["students"]) == 2
    assert len(heatmap["misconceptions"]) == 12
    summary = next(s for s in heatmap["summary"] if s["misconception_id"] == "K01")
    assert summary["students_seen"] == 2

    csv = heatmap_csv(heatmap)
    assert csv.startswith("pseudonim;K01")
    assert "Ola" in csv and "Jan" in csv
    assert len(csv.strip().splitlines()) == 3
