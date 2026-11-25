"""Weryfikator SymPy — jedyne źródło prawdy o poprawności matematyki.

LLM nigdy nie decyduje, czy krok jest poprawny. Ten moduł odpowiada na trzy
pytania:

1. Czy błędny krok Kuby naprawdę jest błędny dla wylosowanych parametrów?
2. Czy krok, który Kuba poda po poprawie, jest poprawny?
3. Jaki kontrprzykład liczbowy pokazać w podpowiedzi?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from app.catalog import Misconception, fill, load_catalog
from app.math.parse import (
    extract_numbers,
    latex_to_sympy_text,
    parse_math,
    split_equation,
    strip_words,
)

DEFAULT_PROBE_VALUES: tuple[Any, ...] = (1, 2, 3, 4, 5, 10, -1, -2, sp.Rational(1, 2))


def _format_number(value: Any) -> str:
    """Czytelny zapis liczby: 16, 7/2, 5.0 → 5."""
    expr = sp.sympify(value)
    if expr.is_Integer:
        return str(int(expr))
    if expr.is_Rational:
        return f"{expr.p}/{expr.q}"
    return sp.sstr(sp.N(expr, 4))


@dataclass
class Counterexample:
    var: str | None
    value: str | None
    lhs_value: str
    rhs_value: str
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "var": self.var,
            "value": self.value,
            "lhs_value": self.lhs_value,
            "rhs_value": self.rhs_value,
            "text": self.text,
        }


@dataclass
class StepVerdict:
    misconception_id: str
    kind: str
    wrong_is_wrong: bool
    correct_is_correct: bool
    counterexample: Counterexample | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.wrong_is_wrong and self.correct_is_correct and self.counterexample is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "misconception_id": self.misconception_id,
            "kind": self.kind,
            "wrong_is_wrong": self.wrong_is_wrong,
            "correct_is_correct": self.correct_is_correct,
            "counterexample": self.counterexample.as_dict() if self.counterexample else None,
            "notes": self.notes,
        }


@dataclass
class CorrectionVerdict:
    accepted: bool
    reason: str
    parsed: str | None = None
    expected: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "parsed": self.parsed,
            "expected": self.expected,
        }


# --------------------------------------------------------------------------- #
# pomocnicze
# --------------------------------------------------------------------------- #


def _sym(expr_text: str, params: dict[str, Any], var: str) -> sp.Expr:
    return sp.sympify(fill(expr_text, params), locals={var: sp.Symbol(var, real=True)})


def as_log10(expr: sp.Expr) -> sp.Expr:
    """Reinterpretuje `log` jako logarytm dziesiętny (tak piszą uczniowie)."""
    try:
        return expr.replace(lambda e: isinstance(e, sp.log), lambda e: sp.log(e.args[0], 10))
    except Exception:  # noqa: BLE001  # pragma: no cover
        return expr


def equivalent(a: sp.Expr, b: sp.Expr) -> bool:
    """Czy dwa wyrażenia są tożsamościowo równe?"""
    try:
        diff = sp.simplify(sp.expand(a - b))
    except Exception:  # noqa: BLE001  # pragma: no cover
        return False
    if diff == 0:
        return True
    # próba numeryczna dla wyrażeń, których simplify nie domknął
    try:
        var_set = (a - b).free_symbols
        if not var_set:
            return bool(sp.N(diff, 12) == 0)
        symbol = next(iter(var_set))
        samples = [sp.Rational(1, 3), 2, sp.Rational(7, 5), 11]
        values = []
        for sample in samples:
            value = sp.N(diff.subs(symbol, sample), 12)
            if not value.is_number or value.has(sp.zoo, sp.nan, sp.oo):
                continue
            values.append(abs(complex(value)))
        return bool(values) and max(values) < 1e-9
    except Exception:  # noqa: BLE001  # pragma: no cover
        return False


def _probe_values(check: dict[str, Any], params: dict[str, Any], var: str) -> list[sp.Expr]:
    raw = check.get("probe_values") or list(DEFAULT_PROBE_VALUES)
    out: list[sp.Expr] = []
    for item in raw:
        if isinstance(item, str):
            out.append(sp.sympify(fill(item, params)))
        else:
            out.append(sp.sympify(item))
    return out


def _safe_eval(expr: sp.Expr, symbol: sp.Symbol | None, value: sp.Expr | None) -> sp.Expr | None:
    try:
        substituted = expr if symbol is None else expr.subs(symbol, value)
        result = sp.nsimplify(sp.simplify(substituted))
        if result.has(sp.zoo, sp.nan, sp.oo, sp.I) or not result.is_real:
            return None
        return result
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# główna weryfikacja
# --------------------------------------------------------------------------- #


def verify_step(item: Misconception, params: dict[str, Any]) -> StepVerdict:
    kind = item.check.get("kind", "expr")
    if kind == "expr":
        return _verify_expr(item, params)
    if kind == "solset":
        return _verify_solset(item, params)
    if kind == "numeric":
        return _verify_numeric(item, params)
    raise ValueError(f"Nieznany rodzaj sprawdzenia: {kind}")  # pragma: no cover


def _verify_expr(item: Misconception, params: dict[str, Any]) -> StepVerdict:
    var = item.var
    symbol = sp.Symbol(var, real=True)
    lhs = _sym(item.check["wrong_lhs"], params, var)
    rhs_wrong = _sym(item.check["wrong_rhs"], params, var)
    rhs_correct = _sym(item.check["correct_rhs"], params, var)

    wrong_is_wrong = not equivalent(lhs, rhs_wrong)
    correct_is_correct = equivalent(lhs, rhs_correct)

    counter = None
    for value in _probe_values(item.check, params, var):
        left = _safe_eval(lhs, symbol, value)
        right = _safe_eval(rhs_wrong, symbol, value)
        if left is None or right is None or sp.simplify(left - right) == 0:
            continue
        counter = Counterexample(
            var=var,
            value=_format_number(value),
            lhs_value=_format_number(left),
            rhs_value=_format_number(right),
            text=(
                f"Dla {var} = {_format_number(value)} lewa strona daje "
                f"{_format_number(left)}, a prawa {_format_number(right)}."
            ),
        )
        break
    return StepVerdict(item.id, "expr", wrong_is_wrong, correct_is_correct, counter)


def _verify_solset(item: Misconception, params: dict[str, Any]) -> StepVerdict:
    var = item.var
    symbol = sp.Symbol(var, real=True)
    check = item.check
    relation = _sym(check["relation"], params, var)

    if "wrong_relation" in check:
        wrong_relation = _sym(check["wrong_relation"], params, var)
        counter = None
        differs = False
        for value in _probe_values(check, params, var):
            try:
                truth_correct = bool(relation.subs(symbol, value))
                truth_wrong = bool(wrong_relation.subs(symbol, value))
            except Exception:  # noqa: BLE001  # pragma: no cover
                continue
            if truth_correct != truth_wrong:
                differs = True
                counter = Counterexample(
                    var=var,
                    value=_format_number(value),
                    lhs_value="spełnia" if truth_correct else "nie spełnia",
                    rhs_value="spełnia" if truth_wrong else "nie spełnia",
                    text=(
                        f"Weź {var} = {_format_number(value)}: wyjściową nierówność "
                        f"{'spełnia' if truth_correct else 'nie spełnia'}, "
                        f"a zapis Kuby mówi, że {'spełnia' if truth_wrong else 'nie spełnia'}."
                    ),
                )
                break
        correct_is_correct = True
        notes = [] if differs else ["Nie znaleziono liczby rozróżniającej zbiory rozwiązań."]
        return StepVerdict(item.id, "solset", differs, correct_is_correct, counter, notes)

    correct_solutions = set(sp.solve(sp.Eq(relation, 0), symbol))
    wrong_solutions = {sp.sympify(fill(str(s), params)) for s in check["wrong_solutions"]}
    wrong_is_wrong = correct_solutions != wrong_solutions
    diff = (correct_solutions ^ wrong_solutions)
    counter = None
    if diff:
        value = sorted(diff, key=lambda v: (sp.N(v) if v.is_number else 0))[0]
        in_correct = value in correct_solutions
        counter = Counterexample(
            var=var,
            value=_format_number(value),
            lhs_value="jest rozwiązaniem" if in_correct else "nie jest rozwiązaniem",
            rhs_value="pominięte" if in_correct else "dopisane",
            text=(
                f"Sprawdź {var} = {_format_number(value)}: "
                + (
                    "spełnia wyjściowe równanie, a w rozwiązaniu Kuby go nie ma."
                    if in_correct
                    else "nie spełnia wyjściowego równania, a Kuba je wypisał."
                )
            ),
        )
    return StepVerdict(item.id, "solset", wrong_is_wrong, True, counter)


def _verify_numeric(item: Misconception, params: dict[str, Any]) -> StepVerdict:
    check = item.check
    lhs = _sym(check["wrong_lhs"], params, item.var)
    rhs_wrong = _sym(check["wrong_rhs"], params, item.var)
    rhs_correct = _sym(check["correct_rhs"], params, item.var)

    wrong_is_wrong = sp.simplify(lhs - rhs_wrong) != 0
    correct_is_correct = sp.simplify(lhs - rhs_correct) == 0
    counter = Counterexample(
        var=None,
        value=None,
        lhs_value=_format_number(sp.simplify(lhs)),
        rhs_value=_format_number(sp.simplify(rhs_wrong)),
        text=(
            f"Policz dokładnie: poprawnie wychodzi {_format_number(sp.simplify(lhs))}, "
            f"a w linijce Kuby jest {_format_number(sp.simplify(rhs_wrong))}."
        ),
    )
    return StepVerdict(item.id, "numeric", wrong_is_wrong, correct_is_correct, counter)


def counterexample_for(item: Misconception, params: dict[str, Any]) -> Counterexample | None:
    return verify_step(item, params).counterexample


# --------------------------------------------------------------------------- #
# poprawka ucznia
# --------------------------------------------------------------------------- #


def check_student_correction(
    item: Misconception, params: dict[str, Any], text: str
) -> CorrectionVerdict:
    """Czy poprawka zaproponowana przez ucznia jest równoważna poprawnemu krokowi?"""
    var = item.var
    check = item.check
    expected_text = fill(check.get("correct_rhs", ""), params)

    if not text or not text.strip():
        return CorrectionVerdict(False, "Brak treści poprawki.")

    if check.get("kind") == "solset" and "wrong_relation" in check:
        return _check_inequality_correction(item, params, text)

    try:
        parts = split_equation(text)
        if parts:
            left = parse_math(parts[0], var)
            right = parse_math(parts[1], var)
            student = sp.simplify(left - right)
        else:
            student = parse_math(text, var)
    except ValueError as exc:
        return CorrectionVerdict(False, str(exc))

    kind = check.get("kind", "expr")

    if kind in {"expr", "numeric"}:
        expected = _sym(check["correct_rhs"], params, var)
        reference_lhs = _sym(check["wrong_lhs"], params, var)
        if parts:
            # uczeń zapisał równanie — sprawdzamy tożsamość lewa − prawa = 0
            if equivalent(student, sp.Integer(0)):
                return CorrectionVerdict(
                    True,
                    "Poprawka jest tożsamością — zgadza się z poprawnym krokiem.",
                    sp.sstr(student),
                    sp.sstr(expected),
                )
            if equivalent(student, sp.simplify(reference_lhs - expected)):
                return CorrectionVerdict(
                    True, "Poprawka równoważna poprawnemu krokowi.", sp.sstr(student), sp.sstr(expected)
                )
            return CorrectionVerdict(
                False, "Poprawka nie jest równoważna poprawnemu krokowi.", sp.sstr(student), sp.sstr(expected)
            )
        variants = [student, as_log10(student)] if student.has(sp.log) else [student]
        accepted = any(
            equivalent(variant, expected) or equivalent(variant, reference_lhs)
            for variant in variants
        )
        return CorrectionVerdict(
            accepted,
            "Poprawka równoważna poprawnemu krokowi."
            if accepted
            else "Poprawka nie jest równoważna poprawnemu krokowi.",
            sp.sstr(student),
            sp.sstr(expected),
        )

    # kind == "solset": porównujemy zbiór wypisanych liczb ze zbiorem rozwiązań
    symbol = sp.Symbol(var, real=True)
    relation = _sym(check["relation"], params, var)
    if "wrong_relation" in check:
        return _check_inequality_correction(item, params, text)
    try:
        correct_solutions = {sp.nsimplify(s) for s in sp.solve(sp.Eq(relation, 0), symbol)}
    except Exception:  # noqa: BLE001  # pragma: no cover
        correct_solutions = set()
    listed = extract_numbers(text)
    accepted = bool(correct_solutions) and listed == correct_solutions
    expected = ", ".join(sorted(sp.sstr(s) for s in correct_solutions)) or expected_text
    return CorrectionVerdict(
        accepted,
        "Wypisane rozwiązania zgadzają się ze zbiorem rozwiązań."
        if accepted
        else "Zbiór rozwiązań się nie zgadza (brakuje rozwiązań albo są nadmiarowe).",
        ", ".join(sorted(sp.sstr(n) for n in listed)),
        expected,
    )


def _check_inequality_correction(
    item: Misconception, params: dict[str, Any], text: str
) -> CorrectionVerdict:
    """Nierówność: poprawka ucznia musi zgadzać się z wyjściową dla liczb testowych."""
    var = item.var
    symbol = sp.Symbol(var, real=True)
    relation = _sym(item.check["relation"], params, var)
    try:
        student_relation = sp.sympify(
            strip_words(latex_to_sympy_text(text), var), locals={var: symbol}
        )
    except Exception:  # noqa: BLE001
        return CorrectionVerdict(False, "Nie udało się odczytać nierówności.")
    if not isinstance(student_relation, sp.core.relational.Relational):
        return CorrectionVerdict(False, "To nie jest nierówność.", sp.sstr(student_relation))

    probes = [sp.Integer(n) for n in (-20, -10, -5, -4, -3, -2, -1, 0, 1, 2, 3, 5, 10, 20)]
    for value in probes:
        try:
            if bool(relation.subs(symbol, value)) != bool(student_relation.subs(symbol, value)):
                return CorrectionVerdict(
                    False,
                    f"Dla {var} = {value} Twój zapis mówi coś innego niż wyjściowa nierówność.",
                    sp.sstr(student_relation),
                    sp.sstr(relation),
                )
        except Exception:  # noqa: BLE001  # pragma: no cover
            continue
    return CorrectionVerdict(
        True, "Zbiór rozwiązań zgadza się z wyjściową nierównością.",
        sp.sstr(student_relation), sp.sstr(relation),
    )


# --------------------------------------------------------------------------- #
# autotest katalogu (uruchamiany przy starcie aplikacji i w pytest)
# --------------------------------------------------------------------------- #


def selfcheck_catalog(max_draws: int | None = None) -> list[StepVerdict]:
    """Sprawdza wszystkie pozycje katalogu dla wszystkich kombinacji parametrów."""
    results: list[StepVerdict] = []
    for item in load_catalog().values():
        draws = item.all_param_draws()
        if max_draws is not None:
            draws = draws[:max_draws]
        for params in draws:
            results.append(verify_step(item, params))
    return results
