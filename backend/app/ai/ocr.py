"""Rozpoznawanie odręcznego zapisu ucznia → LaTeX (model vision).

Kluczowy zakaz w prompcie: model NIE poprawia błędów. Model vision ma
tendencję do „naprawiania” zapisu ucznia, co zafałszowałoby ocenę poprawki.
Przy niskiej pewności aplikacja prosi o potwierdzenie albo o klawiaturę.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.gateway import extract_json, gateway
from app.llm.providers import TASK_OCR

PROMPT_PATH = Path(__file__).parent / "prompts" / "ocr.txt"


class OcrReply(BaseModel):
    latex: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    unreadable: bool = False


@dataclass
class OcrResult:
    latex: str
    confidence: float
    unreadable: bool
    needs_confirmation: bool
    provider: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "latex": self.latex,
            "confidence": round(self.confidence, 2),
            "unreadable": self.unreadable,
            "needs_confirmation": self.needs_confirmation,
            "provider": self.provider,
            "message": self.message,
        }


def _data_url(image: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(image).decode('ascii')}"


def recognize(image: bytes, mime: str = "image/png") -> OcrResult:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _data_url(image, mime)}},
            ],
        }
    ]

    def local_fallback() -> str:
        return OcrReply(latex="", confidence=0.0, unreadable=True).model_dump_json()

    try:
        result = gateway.complete(
            TASK_OCR,
            messages,
            temperature=0.0,
            max_tokens=300,
            schema=OcrReply,
            local_fallback=local_fallback,
        )
        reply = OcrReply.model_validate(extract_json(result.text))
        provider = result.provider
    except Exception:  # noqa: BLE001
        reply = OcrReply(unreadable=True)
        provider = "wbudowany"

    if reply.unreadable or not reply.latex.strip():
        return OcrResult(
            latex="",
            confidence=reply.confidence,
            unreadable=True,
            needs_confirmation=False,
            provider=provider,
            message="Nie udało się odczytać zapisu. Przepisz poprawkę z klawiatury.",
        )

    needs_confirmation = reply.confidence < settings.ocr_confidence_threshold
    return OcrResult(
        latex=reply.latex.strip(),
        confidence=reply.confidence,
        unreadable=False,
        needs_confirmation=needs_confirmation,
        provider=provider,
        message=(
            "Czy dobrze odczytałem?" if needs_confirmation else "Odczytano zapis."
        ),
    )
