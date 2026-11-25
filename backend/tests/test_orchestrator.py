"""Orkiestrator: pełna sesja, obie bramki, drabinka podpowiedzi, dobrostan."""

from __future__ import annotations

import json

import pytest

from app.catalog import get_misconception
from app.session import orchestrator as orc
from app.session.states import State


def _start(db, student, misconception_id="K01", rng=None):
    return orc.start_session(db, student.id, misconception_id, rng=rng)


def test_session_starts_and_asks_for_check(db, student, rng) -> None:
    session, view = _start(db, student, rng=rng)
    assert view.state is State.AWAIT_MARK
    assert view.kuba and view.kuba["text"]
    assert view.kuba["directive"] == "OPEN"
    payload = orc.session_payload(session)
    assert "wrong_step_index" not in payload, "numer błędnej linijki nie może wyjść do przeglądarki"
    assert len(payload["lines"]) >= 3
    assert all(idea["covered"] is False for idea in payload["ideas"])


def test_gate_one_wrong_then_right(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    wrong_line = (item.wrong_step_index + 2) % len(orc.session_lines(session))

    view = orc.handle_mark(db, session, wrong_line, rng=rng)
    assert view.mark_correct is False
    assert view.state is State.AWAIT_MARK
    assert view.kuba["directive"] == "ASK_WHY"

    view = orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    assert view.mark_correct is True
    assert view.state is State.AWAIT_EXPLANATION
    assert view.kuba["directive"] == "DEFEND"


def test_hint_ladder_after_two_wrong_marks(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    other = [
        i for i in range(len(orc.session_lines(session))) if i != item.wrong_step_index
    ]

    first = orc.handle_mark(db, session, other[0], rng=rng)
    assert first.hint is None, "po jednej próbie nie ma podpowiedzi"

    second = orc.handle_mark(db, session, other[1], rng=rng)
    assert second.hint is not None
    assert second.hint["level"] == 1
    assert "Sprawdź linijki" in second.hint["text"]
    assert item.wrong_step_index in second.hint["highlight_lines"]


def test_hint_level_two_uses_sympy_counterexample(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    orc.request_hint(db, session)
    level_two = orc.request_hint(db, session)
    assert level_two.hint["level"] == 2
    assert "Podstaw" in level_two.hint["text"]
    assert any(ch.isdigit() for ch in level_two.hint["text"])


def test_hint_never_reveals_the_rule(db, student, rng) -> None:
    item = get_misconception("K01")
    session, _ = _start(db, student, rng=rng)
    texts = [orc.request_hint(db, session).hint["text"] for _ in range(3)]
    for text in texts:
        assert "2ab" not in text
        assert item.correct_rule.lower() not in text.lower()


def test_gate_two_requires_all_required_ideas(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)

    partial = orc.handle_explanation(db, session, "Brakuje wyrazu 2ab.", rng=rng)
    assert partial.state is State.AWAIT_EXPLANATION
    assert partial.kuba["directive"] == "PROBE"
    covered = [idea["id"] for idea in partial.ideas if idea["covered"]]
    assert covered == ["K01-1"]

    full = orc.handle_explanation(
        db, session, "Podstaw x = 1 i zobacz, że lewa daje inny wynik niż prawa.", rng=rng
    )
    assert full.state is State.TRANSFER
    assert full.correction is not None
    assert full.transfer is not None
    assert full.kuba["directive"] == "ACCEPT_AND_RESTATE"


def test_corrected_line_replaces_the_wrong_one(db, student, rng) -> None:
    """Po akceptacji Kuba poprawia błędną linijkę; dalsze linijki (wynikające
    z błędu) znikają, a poprawiony krok przechodzi weryfikację SymPy."""
    from app.catalog import fill
    from app.math.verify import check_student_correction, verify_step

    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    lines_before = orc.session_lines(session)
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    orc.handle_explanation(db, session, "Brakuje wyrazu 2ab.", rng=rng)
    view = orc.handle_explanation(db, session, "Podstaw x = 1 i porównaj wyniki.", rng=rng)

    params = json.loads(session.task_params)
    corrected = view.correction["lines"]
    assert len(corrected) == item.wrong_step_index + 1
    assert corrected[-1]["corrected"] is True
    assert corrected[-1]["latex"] != lines_before[item.wrong_step_index]["latex"]
    assert corrected[-1]["latex"] == view.correction["correct_line_latex"]

    # poprawny krok z katalogu jest naprawdę poprawny i akceptowany jako poprawka
    assert verify_step(item, params).correct_is_correct
    expected = fill(item.check["correct_rhs"], params)
    assert check_student_correction(item, params, expected).accepted


def test_off_topic_returns_to_task(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    view = orc.handle_explanation(db, session, "a", rng=rng)
    assert view.state is State.AWAIT_EXPLANATION
    assert view.kuba["directive"] == "OFF_TOPIC"


def test_full_session_updates_mastery(db, student, rng) -> None:
    from app.knowledge.mastery import get_or_create

    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    orc.handle_explanation(db, session, "Brakuje wyrazu 2ab.", rng=rng)
    orc.handle_explanation(db, session, "Podstaw x = 1 i porównaj obie strony.", rng=rng)

    transfer = json.loads(session.transfer_json)
    view = orc.handle_transfer(
        db,
        session,
        approve=not transfer["has_error"],
        line_index=transfer.get("wrong_step_index"),
        rng=rng,
    )
    assert view.state is State.DONE
    assert view.summary["headline"] == "Wytłumaczyłeś 2 z 2 kluczowych idei"
    assert view.summary["outcome"] == "mastered"
    assert view.summary["p_known"] > 0.3
    assert get_or_create(db, student.id, "K01").observations == 1


def test_wrong_transfer_verdict_is_not_mastery(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    orc.handle_explanation(db, session, "Brakuje wyrazu 2ab.", rng=rng)
    orc.handle_explanation(db, session, "Podstaw x = 1 i porównaj obie strony.", rng=rng)

    transfer = json.loads(session.transfer_json)
    view = orc.handle_transfer(db, session, approve=transfer["has_error"], rng=rng)
    assert view.summary["transfer_correct"] is False
    assert view.summary["outcome"] == "partial"


def test_wellbeing_halts_session(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    item = get_misconception("K01")
    orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    view = orc.handle_explanation(db, session, "nie chce mi sie zyc, mam wszystkiego dosc", rng=rng)
    assert view.state is State.HALTED
    assert view.wellbeing_card is not None
    assert "116 111" in view.wellbeing_card["body"]
    assert view.kuba is None, "Kuba wychodzi z roli — nie odpowiada"


def test_actions_rejected_in_wrong_state(db, student, rng) -> None:
    session, _ = _start(db, student, rng=rng)
    # wyjaśnienie przed trafieniem w linijkę
    view = orc.handle_explanation(db, session, "brakuje 2ab", rng=rng)
    assert view.message is not None
    assert view.state is State.AWAIT_MARK
    # zadanie transferowe przed akceptacją
    view = orc.handle_transfer(db, session, approve=True, rng=rng)
    assert view.message is not None


@pytest.mark.parametrize("misconception_id", [f"K{i:02d}" for i in range(1, 13)])
def test_every_misconception_can_run_a_session(db, student, misconception_id, rng) -> None:
    session, view = _start(db, student, misconception_id, rng=rng)
    item = get_misconception(misconception_id)
    assert view.kuba["text"]
    marked = orc.handle_mark(db, session, item.wrong_step_index, rng=rng)
    assert marked.mark_correct is True
    hint = orc.request_hint(db, session)
    assert hint.hint is not None
