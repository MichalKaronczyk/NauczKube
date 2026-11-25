"""Lekki parser zapisu matematycznego (LaTeX-ish → SymPy).

Nie używamy `sympy.parsing.latex`, bo wymaga antlr4. Potrzebujemy tylko
podzbioru, w którym piszą uczniowie: potęgi, ułamki, pierwiastki, mnożenie.
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

_REPLACEMENTS = [
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\cdot", "*"),
    (r"\\times", "*"),
    (r"\\div", "/"),
    (r"\\!", ""),
    (r"\\,", " "),
    (r"\\;", " "),
    (r"\\ ", " "),
    (r"\\quad", " "),
    (r"\\qquad", " "),
    (r"\\log", "log"),
    (r"\\ln", "ln"),
    (r"\\pi", "pi"),
    (r"\\mathrm", ""),
    (r"\$", ""),
    (r"\\\[", ""),
    (r"\\\]", ""),
]

_FRAC = re.compile(r"\\(?:d|t)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_SQRT = re.compile(r"\\sqrt\s*\{([^{}]*)\}")
_SQRT_BARE = re.compile(r"\\sqrt\s*([0-9a-zA-Z])")
_POW_BRACE = re.compile(r"\^\s*\{([^{}]*)\}")
_TEXT = re.compile(r"\\(?:text|texttt|textrm|mbox)\s*\{([^{}]*)\}")


def latex_to_sympy_text(text: str) -> str:
    """Zamienia zapis „szkolny”/LaTeX na wyrażenie zrozumiałe dla SymPy."""
    out = text.strip()
    out = _TEXT.sub(r" \1 ", out)
    for pattern, replacement in _REPLACEMENTS:
        out = re.sub(pattern, replacement, out)
    for _ in range(4):  # ułamki i pierwiastki mogą być zagnieżdżone
        out = _FRAC.sub(r"((\1)/(\2))", out)
        out = _SQRT.sub(r"sqrt(\1)", out)
    out = _SQRT_BARE.sub(r"sqrt(\1)", out)
    out = _POW_BRACE.sub(r"**(\1)", out)
    out = out.replace("^", "**")
    out = out.replace("{", "(").replace("}", ")")
    out = out.replace("−", "-").replace("·", "*").replace("×", "*")
    out = re.sub(r"(?<=\d),(?=\d)", ".", out)  # 0,5 → 0.5
    out = re.sub(r"\s+", " ", out).strip()
    return out


ALLOWED_WORDS = {"sqrt", "log", "ln", "exp", "sin", "cos", "tan", "pi", "abs"}
_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?")


def strip_words(text: str, var: str = "x") -> str:
    """Usuwa słowa (np. „czyli”, „zł”), zostawiając samą matematykę."""

    def repl(match: re.Match[str]) -> str:
        word = match.group(0)
        if word.lower() in ALLOWED_WORDS or word == var:
            return word
        return " "

    return _WORD.sub(repl, text)


def extract_numbers(text: str) -> set[sp.Expr]:
    """Wyciąga z tekstu wszystkie liczby (także ujemne i ułamki)."""
    out: set[sp.Expr] = set()
    for raw in NUMBER.findall(strip_words(text)):
        candidate = raw.replace(" ", "").replace(",", ".")
        try:
            out.add(sp.nsimplify(sp.Rational(candidate) if "/" in candidate else sp.sympify(candidate)))
        except Exception:  # noqa: BLE001
            continue
    return out


def parse_math(text: str, var: str = "x") -> sp.Expr:
    """Parsuje wyrażenie; rzuca ValueError przy niepowodzeniu."""
    cleaned = strip_words(latex_to_sympy_text(text), var)
    if not cleaned:
        raise ValueError("Puste wyrażenie")
    local = {var: sp.Symbol(var, real=True)}
    try:
        return parse_expr(
            cleaned,
            local_dict=local,
            transformations=TRANSFORMATIONS,
            evaluate=True,
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Nie udało się odczytać wyrażenia: {text!r}") from exc


def split_equation(text: str) -> tuple[str, str] | None:
    """Dzieli „a = b” na części; zwraca None, gdy nie ma znaku równości."""
    normalized = text.replace("\\ne", "!=").replace("≠", "!=")
    if "=" not in normalized or "!=" in normalized:
        return None
    parts = [p for p in normalized.split("=") if p.strip()]
    if len(parts) < 2:
        return None
    return parts[0], parts[-1]
