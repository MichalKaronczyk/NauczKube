"""Orkiestrator sesji.

Zasada nadrzędna: **kod decyduje, CO robi Kuba; LLM decyduje tylko, JAK to
powie.** Orkiestrator wybiera następny stan i dyrektywę, a persona ubiera ją
w słowa. O „zrozumieniu” decyduje tu kod, na podstawie ewaluatora z walidacją
dowodów i weryfikacji SymPy.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from sqlmodel import Session as DbSession

from app.ai import persona
from app.ai.evaluator import EvaluationResult, evaluate_explanation
from app.ai.safety import WELLBEING_CARD, moderate, scrub_pii
from app.catalog import Misconception, get_misconception
from app.config import settings
from app.knowledge.bkt import observation_is_correct
from app.knowledge.mastery import record_observation
from app.math.generator import generate_task, generate_transfer_task
from app.math.verify import check_student_correction
from app.models import Evaluation, Turn, utcnow
from app.models import Session as LearningSession
from app.session.hints import Hint, build_hint, next_level
from app.session.states import State, accepts_explanation, accepts_mark


@dataclass
class TurnView:
    """Jedna odpowiedź serwera na akcję ucznia."""

    session_id: str
    state: State
    kuba: dict[str, Any] | None = None
    hint: dict[str, Any] | None = None
    mark_correct: bool | None = None
    evaluation: dict[str, Any] | None = None
    correction: dict[str, Any] | None = None
    transfer: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    wellbeing_card: dict[str, str] | None = None
    ideas: list[dict[str, Any]] = field(default_factory=list)
    hints_used: int = 0
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": str(self.state),
            "kuba": self.kuba,
            "hint": self.hint,
            "mark_correct": self.mark_correct,
            "evaluation": self.evaluation,
            "correction": self.correction,
            "transfer": self.transfer,
            "summary": self.summary,
            "wellbeing_card": self.wellbeing_card,
            "ideas": self.ideas,
            "hints_used": self.hints_used,
            "message": self.message,
        }


# --------------------------------------------------------------------------- #
# pomocnicze
# --------------------------------------------------------------------------- #


def _params(session: LearningSession) -> dict[str, Any]:
    return json.loads(session.task_params or "{}")


def _lines(session: LearningSession) -> list[dict[str, Any]]:
    return json.loads(session.lines_json or "[]")


def _covered(session: LearningSession) -> list[str]:
    return json.loads(session.covered_ideas or "[]")


def _set_covered(session: LearningSession, ideas: list[str]) -> None:
    session.covered_ideas = json.dumps(sorted(set(ideas)), ensure_ascii=False)


def _log_turn(
    db: DbSession,
    session: LearningSession,
    role: str,
    text: str,
    *,
    modality: str = "text",
    latex: str | None = None,
    emotion: str | None = None,
) -> Turn:
    turn = Turn(
        session_id=session.id,
        role=role,
        modality=modality,
        text=text,
        latex=latex,
        emotion=emotion,
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return turn


def _idea_progress(item: Misconception, params: dict[str, Any], covered: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": idea.id,
            "text": idea.text,
            "required": idea.required,
            "covered": idea.id in covered,
        }
        for idea in item.render_ideas(params)
    ]


def _idle_seconds(session: LearningSession) -> float:
    last = session.last_activity_at
    if last.tzinfo is None:

        last = last.replace(tzinfo=UTC)
    return max(0.0, (utcnow() - last).total_seconds())


def _touch(session: LearningSession) -> None:
    session.last_activity_at = utcnow()


def _halt_for_wellbeing(db: DbSession, session: LearningSession) -> TurnView:
    """Kuba wychodzi z roli, sesja się zatrzymuje. Treść nie trafia do panelu."""
    session.state = str(State.HALTED)
    session.outcome = "halted"
    session.ended_at = utcnow()
    db.add(session)
    db.commit()
    _log_turn(db, session, "system", "sesja zatrzymana — wsparcie", modality="text")
    return TurnView(
        session_id=session.id,
        state=State.HALTED,
        wellbeing_card=WELLBEING_CARD,
        message="Sesja została zatrzymana.",
    )


# --------------------------------------------------------------------------- #
# start sesji
# --------------------------------------------------------------------------- #


def start_session(
    db: DbSession,
    student_id: str,
    misconception_id: str,
    rng: random.Random | None = None,
) -> tuple[LearningSession, TurnView]:
    rng = rng or random.Random()
    item = get_misconception(misconception_id)
    task = generate_task(misconception_id, rng=rng)

    session = LearningSession(
        student_id=student_id,
        misconception_id=misconception_id,
        task_params=json.dumps({k: str(v) for k, v in task.params.items()}, ensure_ascii=False),
        lines_json=json.dumps(task.lines, ensure_ascii=False),
        state=str(State.INTRO),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    turn = persona.speak(item, task.params, task.lines, persona.OPEN, rng=rng)
    _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)

    session.state = str(State.AWAIT_MARK)
    _touch(session)
    db.add(session)
    db.commit()
    db.refresh(session)

    return session, TurnView(
        session_id=session.id,
        state=State.AWAIT_MARK,
        kuba=turn.as_dict(),
        ideas=_idea_progress(item, task.params, []),
    )


def session_lines(session: LearningSession) -> list[dict[str, Any]]:
    """Linijki rozwiązania Kuby w tej sesji."""
    return _lines(session)


def session_payload(session: LearningSession) -> dict[str, Any]:
    """Dane tablicy wysyłane do przeglądarki — bez numeru błędnej linijki."""
    item = get_misconception(session.misconception_id)
    params = _params(session)
    return {
        "session_id": session.id,
        "misconception_id": session.misconception_id,
        "topic": item.topic,
        "title": item.title,
        "task_latex": item.render_task(params),
        "lines": _lines(session),
        "state": session.state,
        "hints_used": session.hints_used,
        "language": item.language,
        "ideas": _idea_progress(item, params, _covered(session)),
    }


# --------------------------------------------------------------------------- #
# bramka 1: wskazanie błędnej linijki
# --------------------------------------------------------------------------- #


def handle_mark(
    db: DbSession,
    session: LearningSession,
    line_index: int,
    rng: random.Random | None = None,
) -> TurnView:
    rng = rng or random.Random()
    state = State(session.state)
    if not accepts_mark(state):
        return TurnView(
            session_id=session.id,
            state=state,
            message="W tym momencie sesja nie czeka na zakreślenie linijki.",
        )

    item = get_misconception(session.misconception_id)
    params = _params(session)
    lines = _lines(session)
    idle = _idle_seconds(session)

    _log_turn(db, session, "student", f"zakreślono linijkę {line_index + 1}", modality="mark")

    if line_index == item.wrong_step_index:
        turn = persona.speak(item, params, lines, persona.DEFEND, rng=rng)
        _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)
        session.state = str(State.AWAIT_EXPLANATION)
        _touch(session)
        db.add(session)
        db.commit()
        return TurnView(
            session_id=session.id,
            state=State.AWAIT_EXPLANATION,
            kuba=turn.as_dict(),
            mark_correct=True,
            ideas=_idea_progress(item, params, _covered(session)),
            hints_used=session.hints_used,
        )

    session.wrong_marks += 1
    level = next_level(session.hints_used, session.wrong_marks, idle)
    hint: Hint | None = None
    if level > session.hints_used:
        session.hints_used = level
        hint = build_hint(item, params, lines, level)
        if hint is not None:
            _log_turn(db, session, "hint", hint.text)

    turn = persona.speak(item, params, lines, persona.ASK_WHY, rng=rng)
    _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)

    session.state = str(State.AWAIT_MARK)
    _touch(session)
    db.add(session)
    db.commit()

    return TurnView(
        session_id=session.id,
        state=State.AWAIT_MARK,
        kuba=turn.as_dict(),
        hint=hint.as_dict() if hint else None,
        mark_correct=False,
        ideas=_idea_progress(item, params, _covered(session)),
        hints_used=session.hints_used,
    )


# --------------------------------------------------------------------------- #
# bramka 2: wyjaśnienie
# --------------------------------------------------------------------------- #


def handle_explanation(
    db: DbSession,
    session: LearningSession,
    text: str,
    modality: str = "text",
    rng: random.Random | None = None,
) -> TurnView:
    rng = rng or random.Random()
    state = State(session.state)
    if not accepts_explanation(state):
        return TurnView(
            session_id=session.id,
            state=state,
            message="W tym momencie sesja nie czeka na wyjaśnienie.",
        )

    item = get_misconception(session.misconception_id)
    params = _params(session)
    lines = _lines(session)

    safety = moderate(text)
    if safety.wellbeing:
        return _halt_for_wellbeing(db, session)

    safe_text = scrub_pii(text)
    student_turn = _log_turn(db, session, "student", safe_text, modality=modality)

    evaluation: EvaluationResult = evaluate_explanation(item, params, safe_text, lines)
    covered_before = _covered(session)
    covered_now = sorted(set(covered_before) | set(evaluation.covered_ids))
    _set_covered(session, covered_now)

    accepted = not evaluation.off_topic and not evaluation.missing_required(covered_before) and not evaluation.student_errors

    db.add(
        Evaluation(
            turn_id=student_turn.id,
            session_id=session.id,
            ideas_json=json.dumps([i.as_dict() for i in evaluation.ideas], ensure_ascii=False),
            student_errors_json=json.dumps(evaluation.student_errors, ensure_ascii=False),
            rejected_json=json.dumps(evaluation.rejected, ensure_ascii=False),
            accepted=accepted,
            model_used=evaluation.model_used,
        )
    )
    db.commit()

    # --- gałąź 1: uczeń napisał coś niezwiązanego z zadaniem ---
    if evaluation.off_topic and not evaluation.covered_ids:
        turn = persona.speak(
            item, params, lines, persona.OFF_TOPIC, student_text=safe_text, rng=rng
        )
        _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)
        session.state = str(State.AWAIT_EXPLANATION)
        _touch(session)
        db.add(session)
        db.commit()
        return TurnView(
            session_id=session.id,
            state=State.AWAIT_EXPLANATION,
            kuba=turn.as_dict(),
            evaluation=evaluation.as_dict(),
            ideas=_idea_progress(item, params, covered_now),
            hints_used=session.hints_used,
        )

    # --- gałąź 2: uczeń sam powiedział coś błędnego → Kuba dopytuje ---
    if evaluation.student_errors:
        turn = persona.speak(
            item,
            params,
            lines,
            persona.CHALLENGE_STUDENT_ERROR,
            student_error=evaluation.student_errors[0],
            student_text=safe_text,
            rng=rng,
        )
        _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)
        session.state = str(State.AWAIT_EXPLANATION)
        _touch(session)
        db.add(session)
        db.commit()
        return TurnView(
            session_id=session.id,
            state=State.AWAIT_EXPLANATION,
            kuba=turn.as_dict(),
            evaluation=evaluation.as_dict(),
            ideas=_idea_progress(item, params, covered_now),
            hints_used=session.hints_used,
        )

    # --- gałąź 3: brakuje wymaganych idei → naiwne pytanie w pierwszą lukę ---
    missing = [
        idea.id
        for idea in item.render_ideas(params)
        if idea.required and idea.id not in covered_now
    ]
    if missing:
        probe = item.render_probe(missing[0], params)
        turn = persona.speak(
            item, params, lines, persona.PROBE, probe=probe, student_text=safe_text, rng=rng
        )
        _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)
        session.state = str(State.AWAIT_EXPLANATION)
        _touch(session)
        db.add(session)
        db.commit()
        return TurnView(
            session_id=session.id,
            state=State.AWAIT_EXPLANATION,
            kuba=turn.as_dict(),
            evaluation=evaluation.as_dict(),
            ideas=_idea_progress(item, params, covered_now),
            hints_used=session.hints_used,
        )

    # --- gałąź 4: wszystkie wymagane idee zaliczone → Kuba rozumie ---
    return _accept_and_transfer(db, session, item, params, lines, evaluation, rng)


def _accept_and_transfer(
    db: DbSession,
    session: LearningSession,
    item: Misconception,
    params: dict[str, Any],
    lines: list[dict[str, Any]],
    evaluation: EvaluationResult,
    rng: random.Random,
) -> TurnView:
    turn = persona.speak(item, params, lines, persona.ACCEPT_AND_RESTATE, rng=rng)
    _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)

    # Kuba poprawia błędną linijkę; dalsze linijki wynikały z błędu, więc znikają.
    corrected_lines = [dict(line) for line in lines[: item.wrong_step_index + 1]]
    corrected_lines[item.wrong_step_index]["latex"] = item.render_correct_line(params)
    corrected_lines[item.wrong_step_index]["note"] = "poprawione"
    corrected_lines[item.wrong_step_index]["corrected"] = True

    transfer = generate_transfer_task(
        session.misconception_id,
        rng=rng,
        error_probability=settings.transfer_error_probability,
        exclude_params=params,
    )
    session.transfer_json = json.dumps(transfer, ensure_ascii=False)
    session.state = str(State.TRANSFER)
    _touch(session)
    db.add(session)
    db.commit()

    intro = persona.speak(item, params, lines, persona.TRANSFER_INTRO, rng=rng)
    _log_turn(db, session, "kuba", intro.text, emotion=intro.emotion)

    public_transfer = {
        "task_latex": transfer["task_latex"],
        "lines": transfer["lines"],
        "intro": intro.as_dict(),
    }

    return TurnView(
        session_id=session.id,
        state=State.TRANSFER,
        kuba=turn.as_dict(),
        evaluation=evaluation.as_dict(),
        correction={
            "lines": corrected_lines,
            "correct_line_latex": item.render_correct_line(params),
            "wrong_step_index": item.wrong_step_index,
        },
        transfer=public_transfer,
        ideas=_idea_progress(item, params, _covered(session)),
        hints_used=session.hints_used,
    )


# --------------------------------------------------------------------------- #
# poprawka odręczna ucznia (SymPy sprawdza równoważność)
# --------------------------------------------------------------------------- #


def handle_correction_text(
    db: DbSession, session: LearningSession, latex: str
) -> dict[str, Any]:
    item = get_misconception(session.misconception_id)
    params = _params(session)
    verdict = check_student_correction(item, params, latex)
    _log_turn(db, session, "student", latex, modality="ink", latex=latex)
    _touch(session)
    db.add(session)
    db.commit()
    return verdict.as_dict()


# --------------------------------------------------------------------------- #
# zadanie transferowe i podsumowanie
# --------------------------------------------------------------------------- #


def handle_transfer(
    db: DbSession,
    session: LearningSession,
    approve: bool,
    line_index: int | None = None,
    rng: random.Random | None = None,
) -> TurnView:
    rng = rng or random.Random()
    state = State(session.state)
    if state is not State.TRANSFER:
        return TurnView(
            session_id=session.id,
            state=state,
            message="Zadanie transferowe nie jest w tym momencie aktywne.",
        )

    item = get_misconception(session.misconception_id)
    params = _params(session)
    lines = _lines(session)
    transfer = json.loads(session.transfer_json or "{}")
    has_error = bool(transfer.get("has_error"))

    if has_error:
        transfer_correct = (not approve) and line_index == transfer.get("wrong_step_index")
    else:
        transfer_correct = approve

    _log_turn(
        db,
        session,
        "student",
        "zatwierdzono rozwiązanie" if approve else f"zakwestionowano linijkę {(line_index or 0) + 1}",
        modality="mark",
    )

    turn = persona.speak(item, params, lines, persona.THANKS, rng=rng)
    _log_turn(db, session, "kuba", turn.text, emotion=turn.emotion)

    covered = _covered(session)
    required = item.required_idea_ids
    explanation_complete = all(idea_id in covered for idea_id in required)
    correct_observation = observation_is_correct(
        marked_correctly=True,
        explanation_complete=explanation_complete,
        strong_hints_used=max(0, session.hints_used - 1),
        transfer_correct=transfer_correct,
    )

    mastery = record_observation(db, session.student_id, session.misconception_id, correct_observation)

    session.state = str(State.DONE)
    session.outcome = "mastered" if correct_observation else "partial"
    session.ended_at = utcnow()
    _touch(session)
    db.add(session)
    db.commit()

    summary = build_summary(db, session, transfer_correct=transfer_correct, p_known=mastery.p_known)
    return TurnView(
        session_id=session.id,
        state=State.DONE,
        kuba=turn.as_dict(),
        summary=summary,
        ideas=_idea_progress(item, params, covered),
        hints_used=session.hints_used,
    )


def build_summary(
    db: DbSession,
    session: LearningSession,
    *,
    transfer_correct: bool | None = None,
    p_known: float | None = None,
) -> dict[str, Any]:
    item = get_misconception(session.misconception_id)
    params = _params(session)
    covered = _covered(session)
    ideas = _idea_progress(item, params, covered)
    required = [idea for idea in ideas if idea["required"]]
    explained = [idea for idea in required if idea["covered"]]

    if p_known is None:
        from app.knowledge.mastery import get_or_create

        p_known = get_or_create(db, session.student_id, session.misconception_id).p_known

    return {
        "misconception_id": session.misconception_id,
        "title": item.title,
        "topic": item.topic,
        "headline": f"Wytłumaczyłeś {len(explained)} z {len(required)} kluczowych idei",
        "ideas": ideas,
        "kuba_learned": item.correct_rule,
        "kuba_learned_latex": item.correct_rule_latex,
        "correct_line_latex": item.render_correct_line(params),
        "wrong_step_index": item.wrong_step_index,
        "hints_used": session.hints_used,
        "wrong_marks": session.wrong_marks,
        "transfer_correct": transfer_correct,
        "p_known": round(p_known, 3),
        "mastered": p_known >= settings.bkt_mastery_threshold,
        "outcome": session.outcome,
        "curriculum": item.curriculum,
    }


# --------------------------------------------------------------------------- #
# podpowiedź na żądanie / po bezczynności
# --------------------------------------------------------------------------- #


def request_hint(db: DbSession, session: LearningSession) -> TurnView:
    item = get_misconception(session.misconception_id)
    params = _params(session)
    lines = _lines(session)
    level = min(3, session.hints_used + 1)
    session.hints_used = level
    _touch(session)
    db.add(session)
    db.commit()
    hint = build_hint(item, params, lines, level)
    if hint is not None:
        _log_turn(db, session, "hint", hint.text)
    return TurnView(
        session_id=session.id,
        state=State(session.state),
        hint=hint.as_dict() if hint else None,
        hints_used=session.hints_used,
        ideas=_idea_progress(item, params, _covered(session)),
    )
