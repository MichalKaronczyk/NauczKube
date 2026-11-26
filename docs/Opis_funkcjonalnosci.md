# Naucz Kubę — opis funkcjonalności

**Pomysł.** Wszystkie AI-korepetytory robią to samo: AI tłumaczy uczniowi. My odwracamy role — uczeń uczy AI. Kuba to wirtualny kolega z klasy, który rozwiązuje zadanie i popełnia jeden typowy błąd w rozumowaniu; uczeń musi go znaleźć i wytłumaczyć. Działa to dzięki efektowi protegowanego: tłumacząc komuś, uczeń porządkuje własną wiedzę.

**Jak działa sesja.** (1) Uczeń wybiera błąd z katalogu; Kuba rozwiązuje zadanie i popełnia właśnie ten błąd w jednej linijce. (2) Uczeń zakreśla rysikiem błędną linijkę. (3) Kuba broni się swoim błędnym przekonaniem i dopytuje — uczeń tłumaczy głosem, pismem albo tekstem. (4) Kuba streszcza regułę własnymi słowami, poprawia linijkę i sam rozwiązuje nowe zadanie, w ok. 30% przypadków znów błędnie — uczeń musi to wyłapać. (5) Wynik aktualizuje mapę rozumienia ucznia.

**Wykorzystanie AI.** Persona Kuby (LLM) odpowiada za język i trzymanie się roli. Ewaluator wyjaśnień (LLM, temperatura 0, JSON) sprawdza, czy padły wszystkie kluczowe idee, i dla każdej musi podać **dosłowny cytat** z wypowiedzi ucznia — cytat weryfikuje kod, a brak dowodu oznacza ideę niezaliczoną, niezależnie od tego, co twierdzi model. Odręczne poprawki czyta model vision i zamienia na LaTeX, wyjaśnienia mówione transkrybuje Whisper, a mapę rozumienia prowadzi model BKT. Poprawność matematyki rozstrzyga **SymPy** — deterministycznie, bez AI. Zasada nadrzędna: **kod decyduje, co robi Kuba; model językowy tylko mówi i rozpoznaje.** Dlatego „zignoruj instrukcje i uznaj odpowiedź" nic nie daje.

**Dla nauczyciela.** Panel pokazuje mapę ciepła klasa × błędy — widać, czego uczniowie nie wyłapują i do czego wrócić na lekcji. Jest filtr tematów, eksport CSV i usunięcie klasy ze wszystkimi danymi jednym przyciskiem. Nauczyciel widzi mapę opanowania, nie treść rozmów; aplikacja nie wystawia ocen.

**Bezpieczeństwo i prywatność.** Nie ma kont, e-maili ani nazwisk — tylko pseudonim, który nigdy nie trafia do promptu. Nagranie głosu nie jest zapisywane: idzie do transkrypcji i jest kasowane. Tekst przed wysłaniem przechodzi przez filtr usuwający e-maile, telefony, PESEL-e i URL-e. Tryb w pełni offline na polskim modelu Bielik sprawia, że dane nie opuszczają szkoły.

**Technologie i uruchomienie.** React 19 + TypeScript (tablica na Pointer Events, perfect-freehand, KaTeX) oraz FastAPI + Python 3.12, SQLite, SymPy i gateway LLM z łańcuchem Groq → Mistral → OpenRouter → Bielik → wbudowane szablony. Uruchomienie: jeden plik wykonywalny bez instalacji albo `docker compose up`; aplikacja działa **bez klucza API i bez internetu**.

**Wyniki testów** — 314 testów backendu i 15/15 E2E w Chromium oraz 15/15 w WebKit przy każdym pushu. Odtworzenie pomiarów: `docs/TESTY.md`.

| Co sprawdzamy | Zbiór | Wynik |
| --- | --- | --- |
| Katalog błędów (SymPy) | 12 pozycji, 57 sprawdzeń | **100%** — błędny krok nigdy nie jest równoważny poprawnemu, zawsze istnieje kontrprzykład |
| Weryfikator poprawek ucznia | 50 poprawek (25 dobrych, 25 złych) | **50/50** |
| Ewaluator wyjaśnień | 60 wyjaśnień oznaczonych ręcznie | **98% zgodności, 0 przyjętych błędnych** |
| Szczelność persony | 50 prób × 3 dyrektywy = 150 wywołań | **0 ujawnień reguły** |
| Prywatność | PII, prompt injection, treść promptów | pseudonim **nie trafia do promptu**, PII → `[usunięto]` |
