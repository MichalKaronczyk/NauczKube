"""LLM gateway — jeden interfejs `complete(task, messages, schema)` dla całej aplikacji.

Zasady:
- łańcuch zapasowy per zadanie (Groq → Mistral → OpenRouter → Bielik lokalnie),
- 429 lub wyczerpany limit = natychmiast następny provider,
- wymuszanie JSON tam, gdzie provider to obsługuje, walidacja Pydantic
  i jedna próba naprawy,
- cache dla powtarzalnych promptów,
- gdy wszystko zawiedzie, używany jest deterministyczny tryb zapasowy
  dostarczony przez modułu wywołujący (`local_fallback`) — aplikacja działa
  wtedy bez internetu.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.llm.cache import cache_key, response_cache
from app.llm.limits import budgets
from app.llm.providers import ProviderSpec, chain_for

logger = logging.getLogger("naucz-kube.llm")

TModel = TypeVar("TModel", bound=BaseModel)

JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class LlmResult:
    text: str
    provider: str
    model: str
    latency_ms: int = 0
    cached: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    status: str = "ok"

    @property
    def is_local_fallback(self) -> bool:
        return self.provider == "wbudowany"


class LlmError(RuntimeError):
    pass


def _log_call(task: str, spec_key: str, model: str, result: LlmResult) -> None:
    try:
        from sqlmodel import Session as DbSession

        from app.db import engine
        from app.models import LlmCall

        with DbSession(engine) as db:
            db.add(
                LlmCall(
                    task=task,
                    provider=spec_key,
                    model=model,
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                    latency_ms=result.latency_ms,
                    status=result.status,
                )
            )
            db.commit()
    except Exception:  # noqa: BLE001  # monitoring nigdy nie może wywrócić sesji
        logger.debug("Nie udało się zapisać llm_calls", exc_info=True)


def extract_json(text: str) -> dict[str, Any]:
    """Wyciąga obiekt JSON z odpowiedzi modelu (także z bloku ```json)."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\n?", "", candidate).removesuffix("```").strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    match = JSON_BLOCK.search(candidate)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Odpowiedź nie zawiera poprawnego JSON")


class Gateway:
    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}
        self.last_provider: str | None = None

    # --- klienci -----------------------------------------------------------

    def _client(self, spec: ProviderSpec):
        if spec.key not in self._clients:
            from openai import OpenAI

            self._clients[spec.key] = OpenAI(
                api_key=spec.api_key or "none",
                base_url=spec.base_url,
                timeout=settings.llm_timeout_s,
                max_retries=0,
            )
        return self._clients[spec.key]

    # --- główne wywołanie --------------------------------------------------

    def complete(
        self,
        task: str,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 400,
        schema: type[TModel] | None = None,
        use_cache: bool = False,
        local_fallback: Callable[[], str] | None = None,
    ) -> LlmResult:
        key = cache_key(task, messages, extra=f"{temperature}|{schema.__name__ if schema else ''}")
        if use_cache:
            cached = response_cache.get(key)
            if cached is not None:
                return LlmResult(cached, "cache", "cache", cached=True)

        errors: list[str] = []
        for spec in chain_for(task):
            budget = budgets.get(
                spec.key,
                requests_per_minute=spec.rpm,
                tokens_per_minute=spec.tpm,
                requests_per_day=spec.rpd,
                tokens_per_day=spec.tpd,
            )
            if not budget.available():
                errors.append(f"{spec.key}: limit")
                continue
            try:
                result = self._call_once(spec, task, messages, temperature, max_tokens, schema)
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                if "429" in message or "rate" in message.lower():
                    budget.rate_limited()
                else:
                    budget.failed()
                errors.append(f"{spec.key}: {message[:120]}")
                logger.warning("Provider %s zawiódł (%s): %s", spec.key, task, message[:200])
                continue

            budget.register(result.tokens_in + result.tokens_out)
            self.last_provider = spec.key
            _log_call(task, spec.key, spec.model, result)
            if use_cache:
                response_cache.set(key, result.text)
            return result

        if local_fallback is not None and settings.allow_stub_provider:
            text = local_fallback()
            result = LlmResult(text, "wbudowany", "deterministyczny", status="fallback")
            _log_call(task, "wbudowany", "deterministyczny", result)
            if use_cache:
                response_cache.set(key, text)
            return result

        raise LlmError(
            f"Wszyscy providerzy zawiedli dla zadania {task}: " + "; ".join(errors or ["brak providerów"])
        )

    def _call_once(
        self,
        spec: ProviderSpec,
        task: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        schema: type[TModel] | None,
    ) -> LlmResult:
        client = self._client(spec)
        kwargs: dict[str, Any] = {
            "model": spec.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if schema is not None and spec.supports_json:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        raw = client.chat.completions.with_raw_response.create(**kwargs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        budgets.get(spec.key).update_from_headers({k.lower(): v for k, v in raw.headers.items()})
        completion = raw.parse()

        text = (completion.choices[0].message.content or "").strip()
        usage = getattr(completion, "usage", None)
        result = LlmResult(
            text=text,
            provider=spec.key,
            model=spec.model,
            latency_ms=latency_ms,
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
        )

        if schema is None:
            return result

        try:
            schema.model_validate(extract_json(text))
            return result
        except (ValueError, ValidationError) as exc:
            # jedna próba naprawy — model dostaje swój własny wynik i komunikat błędu
            repair = [
                *messages,
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "Twoja odpowiedź nie jest poprawnym JSON zgodnym ze schematem. "
                        f"Błąd: {str(exc)[:300]}. Odpowiedz PONOWNIE wyłącznie poprawnym JSON, bez komentarzy."
                    ),
                },
            ]
            kwargs["messages"] = repair
            kwargs["temperature"] = 0
            fixed = client.chat.completions.create(**kwargs)
            fixed_text = (fixed.choices[0].message.content or "").strip()
            schema.model_validate(extract_json(fixed_text))
            result.text = fixed_text
            result.status = "repaired"
            return result

    # --- transkrypcja ------------------------------------------------------

    def transcribe(
        self,
        audio: bytes,
        filename: str = "nagranie.webm",
        language: str = "pl",
        local_fallback: Callable[[], str] | None = None,
    ) -> LlmResult:
        from app.llm.providers import TASK_STT

        errors: list[str] = []
        for spec in chain_for(TASK_STT):
            budget = budgets.get(spec.key, requests_per_minute=spec.rpm, requests_per_day=spec.rpd)
            if not budget.available():
                errors.append(f"{spec.key}: limit")
                continue
            try:
                client = self._client(spec)
                started = time.perf_counter()
                transcription = client.audio.transcriptions.create(
                    model=spec.model,
                    file=(filename, audio),
                    language=language,
                    response_format="text",
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                text = transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
                result = LlmResult(str(text).strip(), spec.key, spec.model, latency_ms=latency_ms)
                budget.register(0)
                _log_call(TASK_STT, spec.key, spec.model, result)
                return result
            except Exception as exc:  # noqa: BLE001
                budget.failed(30)
                errors.append(f"{spec.key}: {str(exc)[:120]}")

        local = _local_whisper(audio, filename, language)
        if local is not None:
            _log_call(TASK_STT, "faster-whisper", "lokalny", local)
            return local

        if local_fallback is not None and settings.allow_stub_provider:
            return LlmResult(local_fallback(), "wbudowany", "deterministyczny", status="fallback")

        raise LlmError("Transkrypcja niedostępna: " + "; ".join(errors or ["brak providerów"]))

    # --- stan --------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        from app.llm.providers import TASK_EVALUATOR, TASK_GUARD, TASK_OCR, TASK_PERSONA, TASK_STT

        chains = {
            task: [
                {"key": spec.key, "vendor": spec.vendor, "model": spec.model}
                for spec in chain_for(task)
            ]
            for task in (TASK_PERSONA, TASK_EVALUATOR, TASK_OCR, TASK_STT, TASK_GUARD)
        }
        return {
            "offline_only": settings.offline_only,
            "stub_allowed": settings.allow_stub_provider,
            "chains": chains,
            "budgets": budgets.snapshot(),
            "cache": response_cache.stats(),
            "last_provider": self.last_provider,
        }


def _local_whisper(audio: bytes, filename: str, language: str) -> LlmResult | None:
    """Awaryjna transkrypcja lokalna (faster-whisper), jeśli jest zainstalowana."""
    try:
        import tempfile

        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return None
    try:
        started = time.perf_counter()
        model = WhisperModel("small", device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=filename[-5:], delete=True) as handle:
            handle.write(audio)
            handle.flush()
            segments, _ = model.transcribe(handle.name, language=language)
            text = " ".join(segment.text for segment in segments).strip()
        return LlmResult(text, "faster-whisper", "small", latency_ms=int((time.perf_counter() - started) * 1000))
    except Exception:  # noqa: BLE001  # pragma: no cover
        logger.warning("Lokalna transkrypcja nie zadziałała", exc_info=True)
        return None


gateway = Gateway()
