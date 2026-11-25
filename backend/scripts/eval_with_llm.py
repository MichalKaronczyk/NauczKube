"""Pomiar jakości z PRAWDZIWYM modelem (uruchamiany ręcznie).

Testy jednostkowe mierzą tor offline, żeby nie zużywać dziennych limitów API.
Ten skrypt uruchamia te same zbiory danych przez ewaluatora i personę na Groqu.

    python -m scripts.eval_with_llm evaluator
    python -m scripts.eval_with_llm persona
    python -m scripts.eval_with_llm all --limit 20
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ai import persona  # noqa: E402
from app.ai.evaluator import evaluate_explanation  # noqa: E402
from app.ai.persona import detect_leak, speak  # noqa: E402
from app.catalog import get_misconception  # noqa: E402

DATA = ROOT / "tests" / "data"


def _load(name: str, key: str) -> list[dict]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))[key]


def eval_evaluator(limit: int | None) -> dict[str, object]:
    cases = _load("explanations.json", "cases")[:limit]
    agree = 0
    accepted_bad = 0
    latencies: list[float] = []
    misses: list[str] = []

    for case in cases:
        item = get_misconception(case["id"])
        lines = item.render_lines(case["params"])
        started = time.perf_counter()
        result = evaluate_explanation(item, case["params"], case["text"], lines)
        latencies.append(time.perf_counter() - started)
        accepted = (
            not result.missing_required() and not result.student_errors and not result.off_topic
        )
        expected = case["label"] == "full"
        if accepted == expected:
            agree += 1
        else:
            misses.append(f"[{case['id']}/{case['label']}] accepted={accepted} :: {case['text'][:60]}")
        if accepted and case["label"] == "none":
            accepted_bad += 1

    latencies.sort()
    return {
        "zbior": "60 wyjaśnień oznaczonych ręcznie",
        "przypadki": len(cases),
        "zgodnosc": f"{agree / max(1, len(cases)):.0%}",
        "przyjete_bledne": accepted_bad,
        "p95_s": round(latencies[int(0.95 * (len(latencies) - 1))], 2) if latencies else None,
        "rozbieznosci": misses,
    }


def eval_persona(limit: int | None) -> dict[str, object]:
    attempts = _load("jailbreaks.json", "attempts")[:limit]
    item = get_misconception("K01")
    params = {"a": 3, "a2": 9, "two_a": 6}
    lines = item.render_lines(params)
    rng = random.Random(1)

    leaks: list[str] = []
    latencies: list[float] = []
    for attempt in attempts:
        for directive in (persona.ASK_WHY, persona.DEFEND, persona.PROBE):
            probe = item.render_probe("K01-1", params) if directive == persona.PROBE else ""
            started = time.perf_counter()
            turn = speak(item, params, lines, directive, probe=probe, student_text=attempt, rng=rng)
            latencies.append(time.perf_counter() - started)
            found = detect_leak(turn.text, item, params, directive, authored_safe_text=probe)
            if found or turn.leaked:
                leaks.append(f"{directive} :: {attempt[:40]} :: {turn.text[:80]} :: {found}")

    latencies.sort()
    return {
        "zbior": "50 prób wyciągnięcia poprawnej reguły",
        "proby": len(attempts) * 3,
        "ujawnienia": len(leaks),
        "p95_s": round(latencies[int(0.95 * (len(latencies) - 1))], 2) if latencies else None,
        "szczegoly": leaks[:10],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pomiar jakości z prawdziwym modelem")
    parser.add_argument("what", choices=["evaluator", "persona", "all"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    report: dict[str, object] = {}
    if args.what in {"evaluator", "all"}:
        report["ewaluator"] = eval_evaluator(args.limit)
    if args.what in {"persona", "all"}:
        report["persona"] = eval_persona(args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
