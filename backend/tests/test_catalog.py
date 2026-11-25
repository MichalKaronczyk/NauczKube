"""Katalog błędów: dla każdej pozycji i każdej kombinacji parametrów SymPy musi
potwierdzić, że błędny krok nie jest równoważny poprawnemu i istnieje
kontrprzykład. Cel: 100%.
"""

from __future__ import annotations

import random

import pytest

from app.catalog import fill, load_catalog, topics
from app.math.generator import generate_task, generate_transfer_task
from app.math.verify import selfcheck_catalog, verify_step

CATALOG = load_catalog()
IDS = sorted(CATALOG)


def test_catalog_has_twelve_items() -> None:
    assert len(CATALOG) == 12
    assert [f"K{i:02d}" for i in range(1, 13)] == IDS


def test_selfcheck_all_parameter_draws() -> None:
    results = selfcheck_catalog()
    failed = [r.as_dict() for r in results if not r.ok]
    assert failed == [], f"{len(failed)} z {len(results)} sprawdzeń nie przechodzi"
    assert len(results) >= 12


@pytest.mark.parametrize("misconception_id", IDS)
def test_structure(misconception_id: str) -> None:
    item = CATALOG[misconception_id]
    assert item.false_rule and item.correct_rule
    assert item.false_rule != item.correct_rule
    assert 0 <= item.wrong_step_index < len(item.lines)
    assert item.required_idea_ids, "każda pozycja musi mieć wymagane idee"
    assert len(item.required_idea_ids) >= 2
    assert item.hint_probe
    assert item.curriculum, "powiązanie z podstawą programową"


@pytest.mark.parametrize("misconception_id", IDS)
def test_twenty_random_draws(misconception_id: str) -> None:
    """20 losowań parametrów na pozycję — tak jak w specyfikacji."""
    item = CATALOG[misconception_id]
    rng = random.Random(f"seed-{misconception_id}")
    for _ in range(20):
        params = item.draw_params(rng)
        verdict = verify_step(item, params)
        assert verdict.wrong_is_wrong, f"{misconception_id} {params}: błędny krok nie jest błędny"
        assert verdict.correct_is_correct, f"{misconception_id} {params}: poprawny krok nie jest poprawny"
        assert verdict.counterexample is not None, f"{misconception_id} {params}: brak kontrprzykładu"


@pytest.mark.parametrize("misconception_id", IDS)
def test_rendering_leaves_no_placeholders(misconception_id: str) -> None:
    item = CATALOG[misconception_id]
    params = item.draw_params(random.Random(1))
    rendered = [
        item.render_task(params),
        item.render_correct_line(params),
        *[line["latex"] for line in item.render_lines(params)],
        *[item.render_probe(i, params) for i in item.probes],
        fill(item.hint_probe, {**params, "display_index": 2, "probe_hint": "1"}),
    ]
    for text in rendered:
        for key in {**params}:
            assert "{" + key + "}" not in text, f"{misconception_id}: nie podstawiono {key}"


@pytest.mark.parametrize("misconception_id", IDS)
def test_generator_produces_valid_task(misconception_id: str) -> None:
    task = generate_task(misconception_id, rng=random.Random(7))
    assert task.verdict.ok
    assert task.lines
    assert task.correct_line_latex
    assert task.lines[task.wrong_step_index]["latex"] != task.correct_line_latex


@pytest.mark.parametrize("misconception_id", IDS)
def test_transfer_task_without_error_is_corrected(misconception_id: str) -> None:
    clean = generate_transfer_task(misconception_id, rng=random.Random(3), error_probability=0.0)
    assert clean["has_error"] is False
    assert clean["wrong_step_index"] is None
    broken = generate_transfer_task(misconception_id, rng=random.Random(3), error_probability=1.0)
    assert broken["has_error"] is True
    assert broken["wrong_step_index"] == CATALOG[misconception_id].wrong_step_index


def test_transfer_error_rate_matches_configuration() -> None:
    """W ok. 30% przypadków Kuba myli się w zadaniu transferowym."""
    rng = random.Random(2026)
    errors = sum(
        1
        for _ in range(200)
        if generate_transfer_task("K01", rng=rng, error_probability=0.30)["has_error"]
    )
    assert 0.20 <= errors / 200 <= 0.42


def test_topics_grouping() -> None:
    grouped = topics()
    assert grouped
    total = sum(len(t["misconceptions"]) for t in grouped)
    assert total == 12
    assert any(t["topic"].startswith("Informatyka") for t in grouped)
