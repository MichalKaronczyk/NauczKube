"""Maszyna stanów sesji — 8 stanów i 2 bramki decyzyjne.

Bramka 1: trafienie w błędną linijkę (AWAIT_MARK).
Bramka 2: wytłumaczenie wszystkich wymaganych idei (AWAIT_EXPLANATION).
Obie pętle wracają bez podawania odpowiedzi.
"""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    INTRO = "INTRO"                         # Kuba pokazał rozwiązanie i prosi o sprawdzenie
    AWAIT_MARK = "AWAIT_MARK"               # bramka 1: czekamy na zakreślenie linijki
    DEFEND = "DEFEND"                       # trafiona linijka, Kuba się broni
    AWAIT_EXPLANATION = "AWAIT_EXPLANATION"  # bramka 2: czekamy na wyjaśnienie
    PROBE = "PROBE"                         # wyjaśnienie częściowe, Kuba dopytuje
    ACCEPTED = "ACCEPTED"                   # Kuba zrozumiał i poprawia linijkę
    TRANSFER = "TRANSFER"                   # zadanie transferowe do oceny
    DONE = "DONE"                           # podsumowanie
    HALTED = "HALTED"                       # sesja zatrzymana (dobrostan ucznia)


ACTIVE_STATES = {
    State.INTRO,
    State.AWAIT_MARK,
    State.DEFEND,
    State.AWAIT_EXPLANATION,
    State.PROBE,
}

TRANSITIONS: dict[State, set[State]] = {
    State.INTRO: {State.AWAIT_MARK, State.HALTED},
    State.AWAIT_MARK: {State.AWAIT_MARK, State.DEFEND, State.HALTED},
    State.DEFEND: {State.AWAIT_EXPLANATION, State.HALTED},
    State.AWAIT_EXPLANATION: {State.PROBE, State.ACCEPTED, State.AWAIT_EXPLANATION, State.HALTED},
    State.PROBE: {State.AWAIT_EXPLANATION, State.HALTED},
    State.ACCEPTED: {State.TRANSFER, State.HALTED},
    State.TRANSFER: {State.DONE, State.HALTED},
    State.DONE: set(),
    State.HALTED: set(),
}


def can_transition(source: State, target: State) -> bool:
    return target in TRANSITIONS.get(source, set())


def accepts_mark(state: State) -> bool:
    return state in {State.INTRO, State.AWAIT_MARK}


def accepts_explanation(state: State) -> bool:
    return state in {State.DEFEND, State.AWAIT_EXPLANATION, State.PROBE}
