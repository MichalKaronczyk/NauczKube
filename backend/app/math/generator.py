"""Generator zadań: losuje parametry i gwarantuje, że błąd Kuby jest realny.

Gwarancja jest deterministyczna — losowanie powtarzamy aż SymPy potwierdzi, że
błędny krok jest błędny, poprawny krok poprawny i istnieje kontrprzykład.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.catalog import Misconception, get_misconception
from app.math.verify import StepVerdict, verify_step


@dataclass
class Task:
    misconception_id: str
    params: dict[str, Any]
    task_latex: str
    lines: list[dict[str, Any]]
    wrong_step_index: int
    correct_line_latex: str
    verdict: StepVerdict

    def as_dict(self) -> dict[str, Any]:
        return {
            "misconception_id": self.misconception_id,
            "task_latex": self.task_latex,
            "lines": self.lines,
            "wrong_step_index": self.wrong_step_index,
        }


def generate_task(
    misconception_id: str,
    rng: random.Random | None = None,
    exclude_params: dict[str, Any] | None = None,
) -> Task:
    item: Misconception = get_misconception(misconception_id)
    rng = rng or random.Random()

    candidates = item.all_param_draws()
    rng.shuffle(candidates)
    if exclude_params:
        keys = [k for k in exclude_params if k in (item.params or {}) or item.param_sets]
        candidates.sort(
            key=lambda p: all(str(p.get(k)) == str(exclude_params.get(k)) for k in keys)
        )

    last_verdict: StepVerdict | None = None
    for params in candidates:
        verdict = verify_step(item, params)
        last_verdict = verdict
        if verdict.ok:
            return Task(
                misconception_id=item.id,
                params=params,
                task_latex=item.render_task(params),
                lines=item.render_lines(params),
                wrong_step_index=item.wrong_step_index,
                correct_line_latex=item.render_correct_line(params),
                verdict=verdict,
            )
    raise RuntimeError(
        f"Nie udało się wygenerować poprawnego zadania dla {misconception_id}: "
        f"{last_verdict.as_dict() if last_verdict else 'brak parametrów'}"
    )


def generate_transfer_task(
    misconception_id: str,
    rng: random.Random | None = None,
    error_probability: float = 0.30,
    exclude_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Zadanie transferowe: Kuba rozwiązuje nowe zadanie z tego samego szablonu.

    W `error_probability` przypadków popełnia w nim błąd (ten sam schemat
    pomyłki), więc uczeń musi ocenić rozwiązanie, a nie zgadywać.
    """
    rng = rng or random.Random()
    task = generate_task(misconception_id, rng=rng, exclude_params=exclude_params)
    item = get_misconception(misconception_id)

    has_error = rng.random() < error_probability
    # Obie wersje mają TYLE SAMO linijek i kończą się na kroku krytycznym —
    # inaczej uczeń poznawałby odpowiedź po samej długości rozwiązania.
    lines = [dict(line) for line in task.lines[: item.wrong_step_index + 1]]
    if not has_error:
        lines[item.wrong_step_index]["latex"] = task.correct_line_latex
        lines[item.wrong_step_index]["note"] = lines[item.wrong_step_index].get("note", "")

    return {
        "misconception_id": misconception_id,
        "params": {k: str(v) for k, v in task.params.items()},
        "task_latex": task.task_latex,
        "lines": lines,
        "has_error": has_error,
        "wrong_step_index": item.wrong_step_index if has_error else None,
    }
