"""Cache odpowiedzi LLM dla powtarzalnych promptów (oszczędza limity)."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from typing import Any

from app.config import settings


def cache_key(task: str, messages: list[dict[str, Any]], extra: str = "") -> str:
    payload = json.dumps({"task": task, "messages": messages, "extra": extra}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, max_size: int | None = None) -> None:
        self._max = max_size or settings.llm_cache_size
        self._store: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> str | None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self.hits += 1
                return self._store[key]
            self.misses += 1
            return None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"size": len(self._store), "hits": self.hits, "misses": self.misses}


response_cache = ResponseCache()
