"""Bayesian Knowledge Tracing — mapa rozumienia.

Dla każdej pary uczeń × błąd w rozumowaniu trzymamy P(L) — prawdopodobieństwo
opanowania. Parametry startowe (z specyfikacji):
P(L0) = 0,30, P(T) = 0,20, P(G) = 0,15, P(S) = 0,10, próg opanowania 0,95.

Obserwacja „poprawna” = trafione wskazanie + pełne wyjaśnienie bez podpowiedzi
poziomu 2 i 3 + trafna ocena zadania transferowego.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class BktParams:
    p_init: float = settings.bkt_p_init
    p_transit: float = settings.bkt_p_transit
    p_guess: float = settings.bkt_p_guess
    p_slip: float = settings.bkt_p_slip
    mastery_threshold: float = settings.bkt_mastery_threshold


DEFAULT_PARAMS = BktParams()


def posterior(p_known: float, correct: bool, params: BktParams = DEFAULT_PARAMS) -> float:
    """P(L_t | obserwacja)."""
    s, g = params.p_slip, params.p_guess
    if correct:
        numerator = p_known * (1 - s)
        denominator = p_known * (1 - s) + (1 - p_known) * g
    else:
        numerator = p_known * s
        denominator = p_known * s + (1 - p_known) * (1 - g)
    if denominator <= 0:  # pragma: no cover
        return p_known
    return numerator / denominator


def update(p_known: float, correct: bool, params: BktParams = DEFAULT_PARAMS) -> float:
    """P(L_{t+1}) = P(L_t | obs) + (1 - P(L_t | obs)) · P(T)."""
    post = posterior(p_known, correct, params)
    return min(1.0, post + (1 - post) * params.p_transit)


def is_mastered(p_known: float, params: BktParams = DEFAULT_PARAMS) -> bool:
    return p_known >= params.mastery_threshold


def observation_is_correct(
    *,
    marked_correctly: bool,
    explanation_complete: bool,
    strong_hints_used: int,
    transfer_correct: bool | None,
) -> bool:
    """Definicja obserwacji „poprawnej” z specyfikacji."""
    if not (marked_correctly and explanation_complete):
        return False
    if strong_hints_used > 0:
        return False
    if transfer_correct is False:  # noqa: SIM103 — kolejność warunków celowo czytelna
        return False
    return True
