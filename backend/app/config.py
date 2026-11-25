"""Konfiguracja aplikacji — wszystko z zmiennych środowiskowych (plik .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
CATALOG_DIR = BACKEND_DIR / "catalog"
STATIC_DIR = BACKEND_DIR / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- serwer ---
    app_name: str = "Naucz Kubę"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'naucz_kube.db'}"

    # --- klucze API (nigdy nie trafiają do przeglądarki) ---
    groq_api_key: str | None = None
    mistral_api_key: str | None = None
    openrouter_api_key: str | None = None

    # --- adresy zgodne z API OpenAI ---
    groq_base_url: str = "https://api.groq.com/openai/v1"
    mistral_base_url: str = "https://api.mistral.ai/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_base_url: str = "http://localhost:11434/v1"

    # --- modele ---
    groq_persona_model: str = "llama-3.3-70b-versatile"
    groq_persona_model_alt: str = "qwen/qwen3-32b"
    groq_evaluator_model: str = "openai/gpt-oss-120b"
    groq_evaluator_model_alt: str = "openai/gpt-oss-20b"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_guard_model: str = "meta-llama/llama-guard-4-12b"

    mistral_text_model: str = "mistral-small-latest"
    mistral_vision_model: str = "pixtral-12b-2409"
    openrouter_text_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    ollama_model: str = "SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M"

    # --- tryby pracy ---
    offline_only: bool = Field(
        default=False,
        description="Tylko lokalny model (Bielik przez Ollama) — zalecane dla szkół.",
    )
    allow_stub_provider: bool = Field(
        default=True,
        description="Gdy żaden provider nie odpowiada, użyj deterministycznego trybu zapasowego "
        "(szablony po polsku + heurystyczny ewaluator). Aplikacja działa wtedy bez internetu "
        "i bez Ollamy — ale z ubożejszym językiem Kuby.",
    )

    llm_timeout_s: float = 25.0
    llm_cache_size: int = 512

    # --- limity bezpieczeństwa ---
    session_rate_limit: int = 30
    session_rate_window_s: int = 600
    solo_retention_days: int = 30

    # --- parametry BKT ---
    bkt_p_init: float = 0.30
    bkt_p_transit: float = 0.20
    bkt_p_guess: float = 0.15
    bkt_p_slip: float = 0.10
    bkt_mastery_threshold: float = 0.95

    # --- mechanika sesji ---
    hint_after_wrong_marks: int = 2
    hint_idle_seconds: int = 90
    transfer_error_probability: float = 0.30
    evidence_similarity_threshold: float = 0.85
    ocr_confidence_threshold: float = 0.70

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
