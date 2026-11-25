"""Normalizacja tekstu i dopasowanie cytatów-dowodów.

To kod, a nie model, decyduje, czy cytat podany przez ewaluatora naprawdę
występuje w wypowiedzi ucznia.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")

_PL_MAP = str.maketrans(
    {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "a", "Ć": "c", "Ę": "e", "Ł": "l", "Ń": "n",
        "Ó": "o", "Ś": "s", "Ź": "z", "Ż": "z",
    }
)


def normalize(text: str) -> str:
    """Małe litery, bez polskich znaków, bez interpunkcji, pojedyncze spacje."""
    if not text:
        return ""
    lowered = unicodedata.normalize("NFC", text).lower().translate(_PL_MAP)
    lowered = lowered.replace("·", "*").replace("×", "*").replace("−", "-")
    stripped = _PUNCT.sub(" ", lowered)
    return _SPACES.sub(" ", stripped).strip()


def normalize_keep_math(text: str) -> str:
    """Jak `normalize`, ale zachowuje symbole matematyczne."""
    if not text:
        return ""
    lowered = unicodedata.normalize("NFC", text).lower().translate(_PL_MAP)
    lowered = lowered.replace("·", "*").replace("×", "*").replace("−", "-")
    lowered = re.sub(r"[^\w\s\+\-\*/\^\=\(\)\.,<>|]", " ", lowered)
    return _SPACES.sub(" ", lowered).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def evidence_score(utterance: str, evidence: str) -> float:
    """Jak dobrze cytat pasuje do wypowiedzi (0..1).

    Dokładne wystąpienie = 1.0. W przeciwnym razie szukamy najlepszego
    okna o długości cytatu i porównujemy podobieństwo.
    """
    hay = normalize_keep_math(utterance)
    needle = normalize_keep_math(evidence)
    if not needle or not hay:
        return 0.0
    if needle in hay:
        return 1.0
    if len(needle) > len(hay):
        return similarity(hay, needle)

    window = len(needle)
    step = max(1, window // 6)
    best = 0.0
    for start in range(0, len(hay) - window + 1, step):
        best = max(best, similarity(hay[start : start + window], needle))
        if best >= 0.999:
            break
    # cytat może być nieco dłuższy niż fragment — sprawdzamy też szersze okno
    wide = min(len(hay), int(window * 1.4))
    for start in range(0, max(1, len(hay) - wide + 1), step):
        best = max(best, similarity(hay[start : start + wide], needle))
    return best


def contains_keyword(utterance: str, keyword: str) -> bool:
    norm_utterance = normalize_keep_math(utterance)
    norm_keyword = normalize_keep_math(keyword)
    if not norm_keyword:
        return False
    return norm_keyword in norm_utterance


def find_keyword_fragment(utterance: str, keyword: str, radius: int = 28) -> str:
    """Zwraca fragment wypowiedzi wokół trafionego słowa kluczowego (jako dowód)."""
    norm_utterance = normalize_keep_math(utterance)
    norm_keyword = normalize_keep_math(keyword)
    position = norm_utterance.find(norm_keyword)
    if position < 0:
        return ""
    start = max(0, position - radius)
    end = min(len(norm_utterance), position + len(norm_keyword) + radius)
    return norm_utterance[start:end].strip()


def word_ngrams(text: str, size: int) -> set[str]:
    words = normalize(text).split()
    if len(words) < size:
        return set()
    return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}


def sentence_count(text: str) -> int:
    parts = [p for p in re.split(r"[.!?…]+", text.strip()) if p.strip()]
    return len(parts)


def trim_to_two_sentences(text: str) -> str:
    """Persona mówi najwyżej 2 krótkimi zdaniami i 1 pytaniem — wymuszamy to w kodzie.

    Pytanie jest zachowywane nawet wtedy, gdy stoi po dwóch zdaniach: bez niego
    Kuba przestałby dopytywać, a o to w tej aplikacji chodzi.
    """
    cleaned = _SPACES.sub(" ", text.strip())
    parts = [p.strip() for p in re.findall(r"[^.!?…]+[.!?…]?", cleaned) if p.strip()]
    if len(parts) <= 2:
        return cleaned

    kept = parts[:2]
    if parts[-1].endswith("?") and parts[-1] not in kept:
        kept = [*kept, parts[-1]]  # pytanie na końcu zostaje — to ono napędza rozmowę
    return " ".join(kept).strip()
