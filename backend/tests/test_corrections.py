"""Weryfikator poprawek: 50 ręcznie przygotowanych przypadków, cel 100% zgodności."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.catalog import get_misconception
from app.math.verify import check_student_correction

DATA = json.loads((Path(__file__).parent / "data" / "corrections.json").read_text(encoding="utf-8"))
CASES = DATA["cases"]


def test_dataset_is_balanced() -> None:
    good = [c for c in CASES if c["accepted"]]
    bad = [c for c in CASES if not c["accepted"]]
    assert len(CASES) == 50
    assert len(good) == 25
    assert len(bad) == 25


@pytest.mark.parametrize("case", CASES, ids=[f"{i:02d}-{c['id']}" for i, c in enumerate(CASES)])
def test_correction_verdict(case: dict) -> None:
    item = get_misconception(case["id"])
    verdict = check_student_correction(item, case["params"], case["text"])
    assert verdict.accepted is case["accepted"], (
        f"{case['id']} {case['text']!r}: oczekiwano accepted={case['accepted']}, "
        f"otrzymano {verdict.accepted} ({verdict.reason}; parsed={verdict.parsed})"
    )


def test_empty_correction_is_rejected() -> None:
    item = get_misconception("K01")
    assert check_student_correction(item, {"a": 3, "a2": 9, "two_a": 6}, "   ").accepted is False


def test_garbage_correction_is_rejected() -> None:
    item = get_misconception("K01")
    verdict = check_student_correction(item, {"a": 3, "a2": 9, "two_a": 6}, "))((+")
    assert verdict.accepted is False
