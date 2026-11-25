"""Licznik limitów darmowych planów.

Limity na planach darmowych liczone są na organizację, więc trzymamy je
globalnie per provider. Wartości aktualizujemy z nagłówków odpowiedzi
(`x-ratelimit-remaining-*`), a przy 429 nakładamy chwilowy cooldown.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class ProviderBudget:
    name: str
    requests_per_minute: int = 30
    tokens_per_minute: int = 12_000
    requests_per_day: int = 1_000
    tokens_per_day: int = 100_000

    requests_this_minute: int = 0
    tokens_this_minute: int = 0
    requests_today: int = 0
    tokens_today: int = 0

    minute_started: float = field(default_factory=time.monotonic)
    day_started: float = field(default_factory=time.monotonic)
    cooldown_until: float = 0.0
    remaining_requests_header: int | None = None
    remaining_tokens_header: int | None = None

    def _roll(self) -> None:
        now = time.monotonic()
        if now - self.minute_started >= 60:
            self.minute_started = now
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
        if now - self.day_started >= 86_400:
            self.day_started = now
            self.requests_today = 0
            self.tokens_today = 0

    def available(self) -> bool:
        self._roll()
        if time.monotonic() < self.cooldown_until:
            return False
        if self.requests_this_minute >= self.requests_per_minute:
            return False
        if self.tokens_this_minute >= self.tokens_per_minute:
            return False
        if self.requests_today >= self.requests_per_day:
            return False
        if self.tokens_today >= self.tokens_per_day:
            return False
        # noqa poniżej: lista warunków czytana jak lista limitów
        if self.remaining_requests_header is not None and self.remaining_requests_header <= 0:  # noqa: SIM103
            return False
        return True

    def register(self, tokens: int) -> None:
        self._roll()
        self.requests_this_minute += 1
        self.requests_today += 1
        self.tokens_this_minute += tokens
        self.tokens_today += tokens

    def rate_limited(self, retry_after_s: float = 20.0) -> None:
        self.cooldown_until = time.monotonic() + retry_after_s

    def failed(self, cooldown_s: float = 60.0) -> None:
        self.cooldown_until = time.monotonic() + cooldown_s

    def update_from_headers(self, headers: dict[str, str]) -> None:
        def parse(key: str) -> int | None:
            raw = headers.get(key)
            if raw is None:
                return None
            try:
                return int(float(str(raw).rstrip("s")))
            except ValueError:
                return None

        remaining_requests = parse("x-ratelimit-remaining-requests")
        remaining_tokens = parse("x-ratelimit-remaining-tokens")
        if remaining_requests is not None:
            self.remaining_requests_header = remaining_requests
        if remaining_tokens is not None:
            self.remaining_tokens_header = remaining_tokens

    def snapshot(self) -> dict[str, object]:
        self._roll()
        return {
            "provider": self.name,
            "available": self.available(),
            "requests_this_minute": self.requests_this_minute,
            "requests_per_minute": self.requests_per_minute,
            "tokens_today": self.tokens_today,
            "tokens_per_day": self.tokens_per_day,
            "cooldown_s": max(0.0, round(self.cooldown_until - time.monotonic(), 1)),
            "remaining_requests_header": self.remaining_requests_header,
        }


class BudgetRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._budgets: dict[str, ProviderBudget] = {}

    def get(self, name: str, **defaults: int) -> ProviderBudget:
        with self._lock:
            if name not in self._budgets:
                self._budgets[name] = ProviderBudget(name=name, **defaults)
            return self._budgets[name]

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return [b.snapshot() for b in self._budgets.values()]


budgets = BudgetRegistry()
