"""Definicje providerów i łańcuchów zapasowych per zadanie.

Wszyscy providerzy (Groq, Mistral, OpenRouter, Ollama) mają API zgodne z
OpenAI, więc zmiana dostawcy to jedna linijka konfiguracji.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

TASK_PERSONA = "persona"
TASK_EVALUATOR = "evaluator"
TASK_OCR = "ocr"
TASK_GUARD = "guard"
TASK_STT = "stt"


@dataclass(frozen=True)
class ProviderSpec:
    key: str                  # unikalny klucz do licznika limitów
    vendor: str               # groq | mistral | openrouter | ollama
    base_url: str
    api_key: str | None
    model: str
    supports_json: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    rpm: int = 30
    tpm: int = 12_000
    rpd: int = 1_000
    tpd: int = 100_000

    @property
    def usable(self) -> bool:
        if self.vendor == "ollama":
            return True
        return bool(self.api_key)


def _groq(model: str, **kwargs) -> ProviderSpec:
    return ProviderSpec(
        key=f"groq:{model}",
        vendor="groq",
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
        model=model,
        **kwargs,
    )


def _mistral(model: str, **kwargs) -> ProviderSpec:
    return ProviderSpec(
        key=f"mistral:{model}",
        vendor="mistral",
        base_url=settings.mistral_base_url,
        api_key=settings.mistral_api_key,
        model=model,
        rpm=20,
        tpm=20_000,
        rpd=500,
        tpd=500_000,
        **kwargs,
    )


def _openrouter(model: str, **kwargs) -> ProviderSpec:
    return ProviderSpec(
        key=f"openrouter:{model}",
        vendor="openrouter",
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=model,
        rpm=20,
        tpm=20_000,
        rpd=50,          # bez zakupu kredytów: 50 zapytań dziennie
        tpd=100_000,
        **kwargs,
    )


def _ollama(model: str, **kwargs) -> ProviderSpec:
    return ProviderSpec(
        key=f"ollama:{model}",
        vendor="ollama",
        base_url=settings.ollama_base_url,
        api_key="ollama",
        model=model,
        rpm=10_000,
        tpm=10_000_000,
        rpd=1_000_000,
        tpd=1_000_000_000,
        **kwargs,
    )


def chain_for(task: str) -> list[ProviderSpec]:
    """Łańcuch zapasowy: Groq → Mistral → OpenRouter → lokalny Bielik."""
    local = [_ollama(settings.ollama_model)]

    if task == TASK_PERSONA:
        remote = [
            _groq(settings.groq_persona_model, rpm=30, tpm=12_000, rpd=1_000, tpd=100_000),
            _groq(settings.groq_persona_model_alt, rpm=30, tpm=6_000, rpd=1_000, tpd=500_000),
            _groq(settings.groq_vision_model, rpm=30, tpm=30_000, rpd=1_000, tpd=500_000),
            _mistral(settings.mistral_text_model),
            _openrouter(settings.openrouter_text_model),
        ]
    elif task == TASK_EVALUATOR:
        remote = [
            _groq(settings.groq_evaluator_model, rpm=30, tpm=8_000, rpd=1_000, tpd=200_000),
            _groq(settings.groq_evaluator_model_alt, rpm=30, tpm=8_000, rpd=1_000, tpd=200_000),
            _mistral(settings.mistral_text_model),
            _openrouter(settings.openrouter_text_model),
        ]
    elif task == TASK_OCR:
        remote = [
            _groq(settings.groq_vision_model, supports_vision=True, rpm=30, tpm=30_000),
            _mistral(settings.mistral_vision_model, supports_vision=True),
        ]
        local = [_ollama(settings.ollama_model, supports_vision=False)]
    elif task == TASK_GUARD:
        remote = [_groq(settings.groq_guard_model, supports_json=False, rpm=30, tpm=15_000)]
        local = []
    elif task == TASK_STT:
        remote = [
            _groq(settings.groq_stt_model, supports_audio=True, rpm=20, rpd=2_000, tpd=10_000_000)
        ]
        local = []
    else:  # pragma: no cover
        raise ValueError(f"Nieznane zadanie AI: {task}")

    if settings.offline_only:
        return [p for p in local if p.usable]
    return [p for p in (*remote, *local) if p.usable]
