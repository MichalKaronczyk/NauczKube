"""Mowa → tekst (Whisper na Groqu, awaryjnie lokalny faster-whisper).

Nagranie nie jest zapisywane w bazie — zapisujemy wyłącznie transkrypcję,
którą uczeń widzi i może poprawić przed wysłaniem.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.safety import scrub_pii
from app.llm.gateway import gateway


@dataclass
class Transcription:
    text: str
    provider: str
    latency_ms: int
    editable: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "editable": self.editable,
        }


def transcribe(audio: bytes, filename: str = "nagranie.webm") -> Transcription:
    result = gateway.transcribe(
        audio,
        filename=filename,
        language="pl",
        local_fallback=lambda: "",
    )
    return Transcription(
        text=scrub_pii(result.text).strip(),
        provider=result.provider,
        latency_ms=result.latency_ms,
    )
