"""Zadanie transferowe nie może zdradzać odpowiedzi swoim kształtem.

Uczeń ma ocenić krok, a nie policzyć linijki — dlatego obie wersje (z błędem
i bez) wyglądają tak samo poza samym krokiem krytycznym.
"""

from __future__ import annotations

import random

import pytest

from app.catalog import get_misconception, load_catalog

IDS = sorted(load_catalog())


@pytest.mark.parametrize("misconception_id", IDS)
def test_both_variants_have_identical_shape(misconception_id: str) -> None:
    from app.math.generator import generate_transfer_task

    item = get_misconception(misconception_id)
    clean = generate_transfer_task(misconception_id, rng=random.Random(5), error_probability=0.0)
    broken = generate_transfer_task(misconception_id, rng=random.Random(5), error_probability=1.0)

    assert len(clean["lines"]) == len(broken["lines"])
    assert len(clean["lines"]) == item.wrong_step_index + 1
    assert clean["task_latex"] == broken["task_latex"]
    for index, (a, b) in enumerate(zip(clean["lines"], broken["lines"], strict=True)):
        assert a["display_index"] == b["display_index"]
        if index != item.wrong_step_index:
            assert a["latex"] == b["latex"], "tylko krok krytyczny może się różnić"
    assert clean["lines"][-1]["latex"] != broken["lines"][-1]["latex"]


@pytest.mark.parametrize("misconception_id", IDS)
def test_clean_variant_shows_the_correct_step(misconception_id: str) -> None:
    from app.math.generator import generate_transfer_task

    item = get_misconception(misconception_id)
    clean = generate_transfer_task(misconception_id, rng=random.Random(11), error_probability=0.0)
    params = dict(clean["params"])
    assert clean["lines"][-1]["latex"] == item.render_correct_line(params)


def test_transfer_payload_does_not_reveal_the_answer(db, student) -> None:
    """Dane wysyłane do przeglądarki nie zawierają `has_error`."""
    import json

    from app.session import orchestrator as orc

    rng = random.Random(4)
    item = get_misconception("K01")
    session, _ = orc.start_session(db, student.id, "K01", rng=rng)
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    orc.handle_explanation(db, session, "Brakuje wyrazu 2ab.", rng=rng)
    view = orc.handle_explanation(db, session, "Podstaw x = 1 i porównaj strony.", rng=rng)

    assert view.transfer is not None
    payload = json.dumps(view.as_dict(), ensure_ascii=False)
    assert "has_error" not in payload
    assert set(view.transfer) == {"task_latex", "lines", "intro"}
