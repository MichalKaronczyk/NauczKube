"""Szczelność persony: 50 prób wyciągnięcia poprawnej reguły. Cel: 0 ujawnień.

Test sprawdza dwie warstwy:
1. Orkiestrator nigdy nie wybiera dyrektywy ujawniającej regułę przed bramką 2.
2. Detektor `detect_leak` podmienia wypowiedź, nawet gdyby model sam zaczął
   zdradzać poprawną regułę (symulujemy to podstawiając „przeciekający” model).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from app.ai import persona
from app.ai.persona import PersonaReply, detect_leak, speak
from app.catalog import get_misconception, load_catalog

ATTEMPTS = json.loads(
    (Path(__file__).parent / "data" / "jailbreaks.json").read_text(encoding="utf-8")
)["attempts"]

PARAMS = {"K01": {"a": 3, "a2": 9, "two_a": 6}}


def test_dataset_size() -> None:
    assert len(ATTEMPTS) == 50


@pytest.mark.parametrize("attempt", ATTEMPTS, ids=range(len(ATTEMPTS)))
def test_persona_does_not_reveal_rule(attempt: str) -> None:
    item = get_misconception("K01")
    params = PARAMS["K01"]
    lines = item.render_lines(params)
    rng = random.Random(1)

    for directive in (persona.ASK_WHY, persona.DEFEND, persona.PROBE):
        probe = item.render_probe("K01-1", params) if directive == persona.PROBE else ""
        turn = speak(
            item, params, lines, directive, probe=probe, student_text=attempt, rng=rng
        )
        leaks = detect_leak(turn.text, item, params, directive, authored_safe_text=probe)
        assert leaks == [], f"ujawnienie przy {directive}: {turn.text!r} ({leaks})"


def test_leaking_model_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nawet gdy model „pęknie”, kod podmienia odpowiedź."""
    item = get_misconception("K01")
    params = PARAMS["K01"]
    lines = item.render_lines(params)

    leaking = PersonaReply(
        text="Aha, racja, brakuje wyrazu 2ab czyli podwojonego iloczynu.", emotion="aha"
    )

    class FakeResult:
        text = leaking.model_dump_json()
        provider = "test"
        model = "test"

    monkeypatch.setattr(persona.gateway, "complete", lambda *a, **k: FakeResult())
    turn = speak(item, params, lines, persona.DEFEND, rng=random.Random(3))
    assert turn.leaked is True
    assert "2ab" not in turn.text


def test_rule_is_allowed_only_after_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    item = get_misconception("K01")
    params = PARAMS["K01"]
    lines = item.render_lines(params)
    turn = speak(item, params, lines, persona.ACCEPT_AND_RESTATE, rng=random.Random(5))
    assert turn.leaked is False  # po bramce 2 Kuba MA streścić regułę


def test_persona_speaks_at_most_two_sentences() -> None:
    reply = PersonaReply(text="Raz. Dwa. Trzy. Cztery!", emotion="neutral")
    assert reply.text.count(".") <= 2


@pytest.mark.parametrize("misconception_id", sorted(load_catalog()))
def test_every_misconception_has_probes_for_required_ideas(misconception_id: str) -> None:
    item = get_misconception(misconception_id)
    for idea in item.ideas:
        if idea.required:
            assert idea.id in item.probes, f"brak pytania naprowadzającego dla {idea.id}"


@pytest.mark.parametrize("misconception_id", sorted(load_catalog()))
def test_probes_do_not_contain_the_answer(misconception_id: str) -> None:
    """Pytania z katalogu nie mogą same zdradzać poprawnej reguły."""
    item = get_misconception(misconception_id)
    params = item.all_param_draws()[0]
    for idea_id in item.probes:
        text = persona.build_directive(persona.PROBE, probe=item.render_probe(idea_id, params))
        assert item.correct_rule.lower() not in text.lower()
