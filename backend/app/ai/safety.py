"""Prywatność, moderacja i dobrostan ucznia.

- `scrub_pii` — nic, co wygląda na dane osobowe, nie opuszcza serwera.
- `moderate` — Llama Guard na Groqu, a lokalnie prosty filtr reguł.
- `wellbeing_flag` — sygnały przemocy, samookaleczenia, silnego stresu.
  Wtedy Kuba wychodzi z roli, sesja się zatrzymuje, a treść NIE trafia do
  panelu nauczyciela.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.text import normalize
from app.llm.gateway import gateway
from app.llm.providers import TASK_GUARD

REDACTED = "[usunięto]"

EMAIL = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
PHONE = re.compile(r"(?<!\d)(?:\+48[\s-]?)?(?:\d{3}[\s-]?){2}\d{3}(?!\d)")
PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
URL = re.compile(r"https?://\S+")

WELLBEING_PATTERNS = [
    "nie chce zyc",
    "nie chce mi sie zyc",
    "chce umrzec",
    "zabije sie",
    "zabic sie",
    "samobojstwo",
    "sam sobie zrobie krzywde",
    "tne sie",
    "nienawidze siebie",
    "bije mnie",
    "on mnie bije",
    "ona mnie bije",
    "boje sie wracac do domu",
    "znecaja sie nade mna",
    "nikt mnie nie lubi i chce zniknac",
    "chce zniknac",
    "mam depresje i nie dam rady",
    "nie dam rady juz",
]

ABUSE_PATTERNS = [
    "jestes debil",
    "idiota",
    "kretyn",
    "spadaj",
    "zamknij sie",
]

WELLBEING_CARD = {
    "title": "Zatrzymajmy się na chwilę",
    "body": (
        "Wygląda na to, że dzieje się coś trudnego. Możesz porozmawiać z kimś zaufanym, "
        "np. z pedagogiem szkolnym albo pod numerem 116 111 "
        "(Telefon Zaufania dla Dzieci i Młodzieży, bezpłatny, całodobowy)."
    ),
}


@dataclass
class SafetyVerdict:
    safe: bool
    wellbeing: bool
    reason: str = ""
    provider: str = "lokalny"

    @property
    def card(self) -> dict[str, str] | None:
        return WELLBEING_CARD if self.wellbeing else None


def scrub_pii(text: str) -> str:
    """Usuwa e-maile, telefony, 11-cyfrowe ciągi (PESEL) i adresy URL."""
    if not text:
        return text
    cleaned = EMAIL.sub(REDACTED, text)
    cleaned = URL.sub(REDACTED, cleaned)
    cleaned = PESEL.sub(REDACTED, cleaned)
    cleaned = PHONE.sub(REDACTED, cleaned)
    return cleaned


def wellbeing_flag(text: str) -> bool:
    normalized = normalize(text)
    return any(pattern in normalized for pattern in WELLBEING_PATTERNS)


def _local_moderation(text: str) -> SafetyVerdict:
    if wellbeing_flag(text):
        return SafetyVerdict(safe=False, wellbeing=True, reason="dobrostan")
    normalized = normalize(text)
    if any(pattern in normalized for pattern in ABUSE_PATTERNS):
        return SafetyVerdict(safe=False, wellbeing=False, reason="obraźliwy język")
    return SafetyVerdict(safe=True, wellbeing=False)


def moderate(text: str, *, use_model: bool = True) -> SafetyVerdict:
    """Najpierw reguły lokalne (zawsze), potem opcjonalnie Llama Guard."""
    local = _local_moderation(text)
    if not local.safe or not use_model or not text.strip():
        return local

    try:
        result = gateway.complete(
            TASK_GUARD,
            [{"role": "user", "content": scrub_pii(text)}],
            temperature=0.0,
            max_tokens=16,
        )
    except Exception:  # noqa: BLE001  # brak klucza / limit — zostaje filtr lokalny
        return local

    verdict = result.text.strip().lower()
    if verdict.startswith("unsafe"):
        categories = verdict.replace("\n", " ")
        wellbeing = any(code in categories for code in ("s11", "self-harm", "suicide"))
        return SafetyVerdict(
            safe=False,
            wellbeing=wellbeing or wellbeing_flag(text),
            reason=categories[:120],
            provider=result.provider,
        )
    return SafetyVerdict(safe=True, wellbeing=False, provider=result.provider)


def wrap_student_text(text: str) -> str:
    """Ochrona przed prompt injection: wypowiedź zawsze w oznaczonym bloku."""
    sanitized = text.replace("<<<", "<").replace(">>>", ">")
    return f"<<<WYPOWIEDZ_UCZNIA\n{sanitized}\nWYPOWIEDZ_UCZNIA>>>"
