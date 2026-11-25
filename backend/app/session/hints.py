"""Drabinka podpowiedzi.

Podpowiedzi pokazuje szara karta „Podpowiedź”, a nie Kuba — Kuba „nie wie”, że
się myli. Kolejny poziom włącza się po 2 nietrafionych próbach albo po 90 s bez
ruchu. Poprawna reguła nigdy nie jest podawana wprost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.catalog import Misconception, fill
from app.config import settings
from app.math.verify import counterexample_for


@dataclass
class Hint:
    level: int
    title: str
    text: str
    highlight_lines: list[int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "title": self.title,
            "text": self.text,
            "highlight_lines": self.highlight_lines,
        }


def _window(item: Misconception, line_count: int) -> list[int]:
    """Zawężenie: okno linijek wokół błędu, nigdy sama linijka."""
    index = item.wrong_step_index
    start = max(0, index - 1)
    end = min(line_count - 1, index + 1)
    if end - start < 1:
        end = min(line_count - 1, start + 1)
    return list(range(start, end + 1))


def build_hint(
    item: Misconception,
    params: dict[str, Any],
    lines: list[dict[str, Any]],
    level: int,
) -> Hint | None:
    """Poziomy: 1 zawężenie, 2 test liczbowy z SymPy, 3 wskazanie linijki + pytanie."""
    if level <= 0:
        return None
    level = min(level, 3)
    display = item.wrong_step_index + 1

    if level == 1:
        window = _window(item, len(lines))
        human = "–".join(str(i + 1) for i in (window[0], window[-1]))
        return Hint(1, "Podpowiedź", f"Sprawdź linijki {human}.", window)

    if level == 2:
        counter = counterexample_for(item, params)
        if counter is not None and counter.var and counter.value:
            text = (
                f"Podstaw {counter.var} = {counter.value} po obu stronach i porównaj wyniki. "
                f"{counter.text}"
            )
        elif counter is not None:
            text = counter.text
        else:  # pragma: no cover
            text = "Policz obie strony na konkretnych liczbach i porównaj wyniki."
        return Hint(2, "Podpowiedź", text, _window(item, len(lines)))

    probe_hint = ""
    counter = counterexample_for(item, params)
    if counter is not None and counter.value:
        probe_hint = str(counter.value)
    question = fill(
        item.hint_probe,
        {**params, "display_index": display, "probe_hint": probe_hint},
    )
    return Hint(
        3,
        "Podpowiedź",
        f"Przyjrzyj się linijce {display}. {question}".strip(),
        [item.wrong_step_index],
    )


def next_level(current_level: int, wrong_marks: int, idle_seconds: float) -> int:
    """Czy włączyć kolejny poziom podpowiedzi?"""
    earned = wrong_marks // settings.hint_after_wrong_marks
    if idle_seconds >= settings.hint_idle_seconds:
        earned += 1
    return min(3, max(current_level, earned))
