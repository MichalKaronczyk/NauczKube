"""Katalog błędów w rozumowaniu — wczytywanie i wypełnianie szablonów.

Każda pozycja (K01..K12) to plik JSON. Przy starcie aplikacji SymPy sprawdza,
że błędny krok naprawdę jest błędny dla wylosowanych parametrów (patrz
`app.math.verify.selfcheck_catalog`).
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import sympy as sp

from app.config import CATALOG_DIR

PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def fill(template: str, params: dict[str, Any]) -> str:
    """Podstawia `{nazwa}` wartościami z `params`; `{100}` i `{}` zostają nietknięte."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in params:
            return str(params[key])
        return match.group(0)

    return PLACEHOLDER.sub(repl, template)


@dataclass(frozen=True)
class Idea:
    id: str
    required: bool
    text: str
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class Misconception:
    id: str
    topic: str
    title: str
    false_rule: str
    correct_rule: str
    correct_rule_latex: str
    kuba_restate: str
    var: str
    task_latex: str
    lines: tuple[dict[str, Any], ...]
    wrong_step_index: int
    correct_line_latex: str
    check: dict[str, Any]
    ideas: tuple[Idea, ...]
    probes: dict[str, str]
    hint_probe: str
    curriculum: str
    params: dict[str, list[Any]] = field(default_factory=dict)
    param_sets: tuple[dict[str, Any], ...] = ()
    derived: dict[str, str] = field(default_factory=dict)
    language: str | None = None

    @property
    def required_idea_ids(self) -> list[str]:
        return [i.id for i in self.ideas if i.required]

    def idea(self, idea_id: str) -> Idea | None:
        return next((i for i in self.ideas if i.id == idea_id), None)

    # --- losowanie parametrów ---------------------------------------------

    def draw_params(self, rng: random.Random | None = None) -> dict[str, Any]:
        rng = rng or random.Random()
        if self.param_sets:
            base = dict(rng.choice(list(self.param_sets)))
        else:
            base = {name: rng.choice(values) for name, values in self.params.items()}
        return self.with_derived(base)

    def all_param_draws(self) -> list[dict[str, Any]]:
        """Wszystkie kombinacje parametrów — używane w testach katalogu."""
        if self.param_sets:
            return [self.with_derived(dict(p)) for p in self.param_sets]
        names = list(self.params)
        combos: list[dict[str, Any]] = [{}]
        for name in names:
            combos = [{**c, name: v} for c in combos for v in self.params[name]]
        return [self.with_derived(c) for c in combos]

    def with_derived(self, base: dict[str, Any]) -> dict[str, Any]:
        out = dict(base)
        for name, expr in self.derived.items():
            value = sp.nsimplify(sp.sympify(expr, locals={k: sp.Integer(v) if isinstance(v, int) else v for k, v in out.items()}))
            if value == int(value):
                out[name] = int(value)
            else:
                out[name] = sp.nsimplify(value)
        return out

    # --- renderowanie ------------------------------------------------------

    def render_lines(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        rendered = []
        for index, line in enumerate(self.lines):
            item = {
                "index": index,
                "display_index": index + 1,
                "latex": fill(line.get("latex", ""), params),
                "note": fill(line.get("note", ""), params),
            }
            if "code" in line:
                item["code"] = fill(line["code"], params)
            rendered.append(item)
        return rendered

    def render_task(self, params: dict[str, Any]) -> str:
        return fill(self.task_latex, params)

    def render_correct_line(self, params: dict[str, Any]) -> str:
        return fill(self.correct_line_latex, params)

    def render_ideas(self, params: dict[str, Any]) -> list[Idea]:
        return [
            Idea(
                id=i.id,
                required=i.required,
                text=fill(i.text, params),
                keywords=tuple(fill(k, params) for k in i.keywords),
            )
            for i in self.ideas
        ]

    def render_probe(self, idea_id: str, params: dict[str, Any]) -> str:
        return fill(self.probes.get(idea_id, "A dlaczego?"), params)


def _parse(raw: dict[str, Any]) -> Misconception:
    return Misconception(
        id=raw["id"],
        topic=raw["topic"],
        title=raw.get("title", raw["id"]),
        false_rule=raw["false_rule"],
        correct_rule=raw["correct_rule"],
        correct_rule_latex=raw.get("correct_rule_latex", ""),
        kuba_restate=raw.get("kuba_restate", ""),
        var=raw.get("var", "x"),
        task_latex=raw["task_latex"],
        lines=tuple(raw["lines"]),
        wrong_step_index=int(raw["wrong_step_index"]),
        correct_line_latex=raw["correct_line_latex"],
        check=raw["check"],
        ideas=tuple(
            Idea(
                id=i["id"],
                required=bool(i.get("required", False)),
                text=i["text"],
                keywords=tuple(i.get("keywords", ())),
            )
            for i in raw["ideas"]
        ),
        probes=dict(raw.get("probes", {})),
        hint_probe=raw.get("hint_probe", ""),
        curriculum=raw.get("curriculum", ""),
        params={k: list(v) for k, v in raw.get("params", {}).items()},
        param_sets=tuple(raw.get("param_sets", ())),
        derived=dict(raw.get("derived", {})),
        language=raw.get("language"),
    )


@lru_cache
def load_catalog() -> dict[str, Misconception]:
    items: dict[str, Misconception] = {}
    for path in sorted(CATALOG_DIR.glob("K*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        items[raw["id"]] = _parse(raw)
    if not items:  # pragma: no cover
        raise RuntimeError(f"Katalog błędów jest pusty: {CATALOG_DIR}")
    return items


def get_misconception(misconception_id: str) -> Misconception:
    catalog = load_catalog()
    if misconception_id not in catalog:
        raise KeyError(f"Nieznany błąd w katalogu: {misconception_id}")
    return catalog[misconception_id]


def topics() -> list[dict[str, Any]]:
    """Lista tematów dla ekranu „Tematy”."""
    grouped: dict[str, list[Misconception]] = {}
    for item in load_catalog().values():
        grouped.setdefault(item.topic, []).append(item)
    return [
        {
            "topic": topic,
            "misconceptions": [
                {"id": m.id, "title": m.title, "curriculum": m.curriculum}
                for m in sorted(items, key=lambda m: m.id)
            ],
        }
        for topic, items in sorted(grouped.items())
    ]
