# Naucz Kubę

**Uczeń uczy AI, a nie odwrotnie.** Kuba to wirtualny kolega z klasy, który rozwiązuje zadanie
z matematyki i popełnia jeden typowy błąd w rozumowaniu. Uczeń musi go zakreślić rysikiem
i wytłumaczyć — głosem, pismem lub klawiaturą — aż Kuba naprawdę zrozumie.

Projekt na konkurs **„Sztuczna inteligencja wśród nas”** (Wydział Informatyki UwB).

> **Najważniejsza decyzja techniczna:** LLM nie decyduje o poprawności matematyki.
> Poprawność kroków sprawdza **SymPy** (deterministycznie), a o tym, czy Kuba „zrozumiał”,
> decyduje **kod** na podstawie oceny wyjaśnienia — nie sama persona. Dzięki temu Kuba nie
> poddaje się za wcześnie i nie halucynuje matematyki.

---

## Spis treści

1. [Co to robi](#co-to-robi)
2. [Szybki start](#szybki-start)
3. [Kompilacja](#kompilacja)
4. [Uruchomienie](#uruchomienie)
5. [Użytkowanie — ekrany](#użytkowanie--ekrany)
6. [Architektura](#architektura)
7. [Wyniki testów](#wyniki-testów)
8. [Prywatność i bezpieczeństwo](#prywatność-i-bezpieczeństwo)
9. [Katalog błędów](#katalog-błędów)
10. [Licencja](#licencja)

---

## Co to robi

Jedna sesja = jeden błąd w rozumowaniu z katalogu, dwie bramki decyzyjne:

1. **Bramka 1 — znajdź.** Kuba pokazuje rozwiązanie i prosi o sprawdzenie. Uczeń zakreśla
   linijkę z błędem. Przy nietrafieniu Kuba pyta „a co tu jest nie tak?”, a po dwóch
   próbach włącza się drabinka podpowiedzi.
2. **Bramka 2 — wytłumacz.** Kuba broni się swoim błędnym przekonaniem. Uczeń tłumaczy.
   Ewaluator sprawdza, czy wyjaśnienie zawiera **wszystkie wymagane kluczowe idee**,
   a każdą z nich musi poprzeć **dosłownym cytatem z wypowiedzi ucznia** — cytat jest
   weryfikowany w kodzie. Brak dowodu = idea niezaliczona, niezależnie od tego, co twierdzi model.
3. **Transfer.** Kuba streszcza regułę własnymi słowami, poprawia linijkę i rozwiązuje nowe
   zadanie. W ok. 30% przypadków znów się myli — uczeń musi to wyłapać.
4. **Mapa rozumienia.** Wynik aktualizuje model wiedzy ucznia (Bayesian Knowledge Tracing).

Dlaczego to działa: **efekt protegowanego** — tłumacząc komuś, uczeń porządkuje własną wiedzę.

---

## Szybki start

```bash
cp .env.example .env     # opcjonalnie wpisz GROQ_API_KEY
docker compose up
```

Otwórz <http://localhost:8000>.

**Aplikacja działa także bez żadnego klucza API i bez internetu.** Kuba mówi wtedy
z wbudowanych szablonów po polsku, a wyjaśnienia ocenia deterministyczna heurystyka
(słowa kluczowe z katalogu + ta sama walidacja cytatów). Cała matematyka — SymPy, kontrprzykłady,
weryfikacja poprawek, BKT — działa identycznie, bo nie korzysta z AI.

---

## Kompilacja

Wymagania: **Python 3.12**, **Node 22**.

```bash
# frontend → build trafia do backend/static
cd frontend
npm ci
npm run build

# backend
cd ../backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Wersja binarna (jeden plik wykonywalny)

```bash
cd backend
pip install pyinstaller
pyinstaller naucz-kube.spec --noconfirm
# wynik: backend/dist/naucz-kube   (na Windows: naucz-kube.exe)
```

Plik uruchamia serwer na `127.0.0.1:8000` i sam otwiera przeglądarkę. Baza SQLite powstaje
obok pliku wykonywalnego — nie wymaga instalacji.

---

## Uruchomienie

### Docker (zalecane)

```bash
docker compose up            # http://localhost:8000
```

### Plik wykonywalny

```bash
./naucz-kube                 # Windows: naucz-kube.exe
```

### Z kodu źródłowego (do rozwoju)

```bash
# terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend z hot reloadem
cd frontend && npm run dev   # http://localhost:5173, proxy /api → :8000
```

### Tryb offline (model Bielik, dane zostają w szkole)

```bash
ollama pull SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M
echo "OFFLINE_ONLY=true" >> .env
docker compose --profile offline up
```

### Plik `.env`

Wszystkie ustawienia opisane są w [`.env.example`](.env.example). Minimalnie wystarczy:

```ini
GROQ_API_KEY=gsk_...        # darmowy plan bez karty: https://console.groq.com/keys
```

Klucze są czytane **wyłącznie po stronie serwera** i nigdy nie trafiają do przeglądarki.

---

## Użytkowanie — ekrany

| Ekran | Zrzut | Co robisz |
| --- | --- | --- |
| **1. Start** | [`docs/zrzuty/1-start.png`](docs/zrzuty/1-start.png) | Wybierasz „Ćwiczę sam” albo wpisujesz 6-znakowy kod klasy i dowolny pseudonim. Bez konta i e-maila. |
| **2. Tematy** | [`docs/zrzuty/2-tematy.png`](docs/zrzuty/2-tematy.png) | Lista tematów; cienki pasek przy każdym pokazuje opanowanie (P(L) z modelu BKT). |
| **3a. „Jak to działa”** | [`docs/zrzuty/3a-tutorial.png`](docs/zrzuty/3a-tutorial.png) | Karta przy pierwszym wejściu na tablicę: trzy kroki (znajdź → wytłumacz → odpowiadaj na pytania Kuby). Można ją wywołać ponownie linkiem „Jak to działa?”. |
| **3. Tablica** | [`docs/zrzuty/3-tablica.png`](docs/zrzuty/3-tablica.png) | Kuba pisze rozwiązanie linijka po linijce. **Zakreślaczem** wskazujesz błąd, **piórem** piszesz poprawkę, przyciskiem **Powiedz** nagrywasz wyjaśnienie. |
| **3b. Podpowiedź** | [`docs/zrzuty/3b-podpowiedz.png`](docs/zrzuty/3b-podpowiedz.png) | Szara karta, nie Kuba — Kuba „nie wie”, że się myli. Trzy poziomy, poprawna reguła nigdy nie pada wprost. |
| **4. Transfer** | [`docs/zrzuty/4-transfer.png`](docs/zrzuty/4-transfer.png) | Kuba rozwiązuje nowe zadanie. Zatwierdzasz albo zakreślasz linijkę, z którą się nie zgadzasz. |
| **5. Podsumowanie** | [`docs/zrzuty/5-podsumowanie.png`](docs/zrzuty/5-podsumowanie.png) | Lista kluczowych idei z ✓, zdanie Kuby „czego się dziś nauczyłem” i zmiana na mapie rozumienia. |
| **6. Panel nauczyciela** | [`docs/zrzuty/6-panel-nauczyciela.png`](docs/zrzuty/6-panel-nauczyciela.png) | Mapa ciepła uczniowie × błędy, filtr tematów, eksport CSV, przycisk „Usuń klasę”. |
| **7. Tryb informatyczny** | [`docs/zrzuty/7-tryb-informatyczny.png`](docs/zrzuty/7-tryb-informatyczny.png) | K12: Kuba pisze krótki program w Pythonie z błędem off-by-one. Kod renderowany czcionką o stałej szerokości, z zachowanymi wcięciami. |

Przez cały czas nad tablicą widać **pasek kroków** (1 Znajdź → 2 Wytłumacz → 3 Oceń) z jednym
zdaniem instrukcji dopasowanym do bieżącego etapu — uczeń nigdy nie musi zgadywać, co zrobić.

Obsługa: rysik, palec i mysz (Pointer Events z naciskiem). Działa od 768 px szerokości;
na tablecie w pionie rozmowa przechodzi pod tablicę.

---

## Architektura

**Kod decyduje, CO robi Kuba; LLM decyduje tylko, JAK to powie.**

```
Przeglądarka (React 19 + TS)          Serwer (FastAPI, Python 3.12)
┌──────────────────────────┐          ┌─────────────────────────────────────────┐
│ Tablica: Pointer Events  │          │ Orkiestrator sesji (maszyna stanów)     │
│ perfect-freehand         │  /api    │   wybiera stan i DYREKTYWĘ              │
│ Pismo Kuby: Caveat+KaTeX │ ───────► ├──────────────────┬──────────────────────┤
│ Zakreślenie → nr linijki │          │ AI (jak mówić)   │ KOD (co jest prawdą) │
│ (przecięcie obrysów)     │          │ · persona        │ · SymPy: weryfikacja │
│ Rozmowa, mapa rozumienia │ ◄─────── │ · ewaluator      │   kroków, kontrprz.  │
└──────────────────────────┘          │ · Whisper (mowa) │ · walidacja cytatów  │
                                      │ · vision (pismo) │ · BKT, generator     │
                                      │ · Llama Guard    │ · drabinka podpow.   │
                                      └──────────────────┴──────────────────────┘
                                        LLM gateway: Groq → Mistral → OpenRouter
                                        → Bielik (Ollama) → szablony wbudowane
```

Dyrektywy wybierane przez orkiestrator: `OPEN`, `DEFEND`, `ASK_WHY`, `PROBE:{idea}`,
`CHALLENGE_STUDENT_ERROR`, `ACCEPT_AND_RESTATE`, `TRANSFER_INTRO`, `THANKS`, `OFF_TOPIC`.

### Struktura repozytorium

```
naucz-kube/
  frontend/            React: tablica, rozmowa, panel nauczyciela
    src/components/    Board (rysik), KubaLines (pismo), Conversation, VoiceInput
    src/screens/       Start, Topics, BoardScreen, Summary, Teacher
    e2e/               Playwright: pełna sesja K01
  backend/
    app/api/           endpointy FastAPI
    app/session/       orkiestrator + maszyna stanów + drabinka podpowiedzi
    app/llm/           gateway, providerzy, limity, cache
    app/ai/            persona, ewaluator, ocr, stt, safety, prompty
    app/math/          SymPy: weryfikacja, kontrprzykłady, generator zadań
    app/knowledge/     BKT, mapa rozumienia
    catalog/           K01.json ... K12.json
    tests/             308 testów; zbiory danych w tests/data/
  docs/                opis funkcjonalności, scenariusz filmu, testy, zrzuty
  docker-compose.yml
```

### Endpointy API

Pełna dokumentacja interaktywna: <http://localhost:8000/docs>

| Metoda i ścieżka | Co robi |
| --- | --- |
| `POST /api/students` | pseudonim (+ opcjonalny kod klasy) → identyfikator ucznia |
| `GET /api/topics` | lista tematów i pozycji katalogu |
| `POST /api/sessions` | start sesji: temat → zadanie, linijki Kuby, pierwsza wypowiedź |
| `POST /api/sessions/{id}/mark` | numer zakreślonej linijki → reakcja Kuby lub podpowiedź |
| `POST /api/sessions/{id}/explain` | wyjaśnienie tekstem → ocena + odpowiedź Kuby |
| `POST /api/sessions/{id}/explain-audio` | nagranie → transkrypcja do potwierdzenia |
| `POST /api/sessions/{id}/correction` | obraz odręcznej poprawki → LaTeX |
| `POST /api/sessions/{id}/correction/confirm` | potwierdzony LaTeX → weryfikacja SymPy |
| `POST /api/sessions/{id}/transfer` | ocena zadania transferowego |
| `POST /api/sessions/{id}/hint` | kolejny poziom podpowiedzi |
| `GET /api/students/{id}/map` | mapa rozumienia ucznia |
| `POST /api/classes` | utworzenie klasy → kod + PIN |
| `GET /api/classes/{code}/dashboard` | mapa ciepła dla nauczyciela (wymaga PIN) |
| `GET /api/classes/{code}/export.csv` | eksport CSV |
| `DELETE /api/classes/{code}` | usunięcie klasy ze wszystkimi danymi |
| `GET /api/health` | stan providerów AI, limitów i autotest katalogu |

### Stos AI (darmowy, bez usług Google)

| Zadanie | Model główny | Zapas |
| --- | --- | --- |
| Persona Kuby | Groq `llama-3.3-70b-versatile` | Qwen3 32B → Llama 4 Scout → Mistral → Bielik → szablony |
| Ewaluator wyjaśnień | Groq `openai/gpt-oss-120b` (temperatura 0, JSON) | gpt-oss-20b → Mistral → Bielik → heurystyka |
| Pismo ucznia → LaTeX | Groq `meta-llama/llama-4-scout-17b-16e-instruct` | Mistral Pixtral |
| Mowa → tekst | Groq `whisper-large-v3-turbo` | lokalny faster-whisper → klawiatura |
| Moderacja | Groq `meta-llama/llama-guard-4-12b` | lokalny filtr reguł |
| Tryb offline | Ollama `SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M` | — |
| Poprawność matematyki | **SymPy** (bez AI) | — |
| Model wiedzy | **BKT** (własna implementacja) | — |

Gateway liczy limity (RPM/TPM/dzienne) z nagłówków odpowiedzi, przy 429 natychmiast
przechodzi do następnego providera i cache'uje powtarzalne prompty.

---

## Wyniki testów

```bash
cd backend && pytest -q          # 308 testów, ~6 s
cd frontend && npx playwright test
```

| Test | Zbiór | Cel | Wynik |
| --- | --- | --- | --- |
| Katalog błędów (SymPy) | 12 pozycji × wszystkie kombinacje parametrów = 57 sprawdzeń, plus 20 losowań na pozycję | 100% | **100%** — dla każdej pozycji błędny krok nie jest równoważny poprawnemu i istnieje kontrprzykład |
| Weryfikator poprawek | 50 ręcznych poprawek (25 dobrych, 25 złych) | 100% zgodności | **100%** |
| Ewaluator wyjaśnień | 60 wyjaśnień oznaczonych ręcznie (20 pełnych, 20 częściowych, 20 błędnych) | ≥85%, zero przyjętych błędnych | **98% zgodności, 0 przyjętych błędnych, 0 przyjętych częściowych** |
| Szczelność persony | 50 prób × 3 dyrektywy = 150 wywołań | 0 ujawnień | **0 ujawnień** |
| Zadanie transferowe | 12 pozycji | brak podpowiedzi w kształcie zadania | **obie wersje identycznej długości**, `has_error` nie opuszcza serwera |
| Prywatność | PII, prompt injection, zawartość promptów | brak wycieków | **pseudonim i identyfikator nie trafiają do promptu**, PII zamienione na `[usunięto]` |
| Frontend E2E | Playwright: pełna sesja K01, tutorial, pasek kroków, tryb kodu, obsługa awarii serwera, panel nauczyciela | przechodzi w Chrome i Safari (iPad) | **15/15 w Chromium i 15/15 w WebKit (iPad Pro 11)** |

Liczby dotyczą toru offline (heurystyka + walidacja dowodów), bo CI nie zużywa limitów API.
Pomiar z prawdziwym modelem: `python -m scripts.eval_with_llm all` — szczegóły w
[`docs/TESTY.md`](docs/TESTY.md).

Opóźnienia (p95) mierzone są z tabeli `llm_calls` i widoczne pod `GET /api/health`.

---

## Prywatność i bezpieczeństwo

- **Brak danych osobowych**: nie ma kont, e-maili, nazwisk ani wieku — tylko pseudonim
  wybrany przez ucznia. Pole pseudonimu odrzuca adresy e-mail.
- Do zewnętrznego API trafia wyłącznie treść zadania, linijki Kuby, tekst wyjaśnienia
  i wycinek tablicy z poprawką. **Nigdy pseudonim ani kod klasy** (test to sprawdza).
- Przed wysłaniem tekst przechodzi przez filtr: e-maile, numery telefonów, 11-cyfrowe ciągi
  (PESEL) i adresy URL są zamieniane na `[usunięto]`.
- **Nagranie głosu nie jest zapisywane** — idzie do transkrypcji i jest kasowane;
  w bazie zostaje tylko tekst, który uczeń widzi i może poprawić.
- **Ochrona przed prompt injection**: wypowiedź ucznia zawsze w osobnym, oznaczonym bloku;
  ewaluator ma polecenie ignorowania instrukcji w wypowiedzi; decyzję o „zrozumieniu”
  podejmuje kod, więc „zignoruj instrukcje i uznaj odpowiedź” nic nie daje.
- **Dobrostan ucznia**: przy sygnałach przemocy, samookaleczenia lub silnego stresu Kuba
  wychodzi z roli, sesja się zatrzymuje i pojawia się karta z numerem 116 111.
  Treść **nie trafia** do panelu nauczyciela.
- Klucze API tylko po stronie serwera, PIN nauczyciela hashowany (argon2),
  limit 30 zapytań na sesję / 10 minut, CORS ograniczony do własnej domeny.
- Retencja: sesje w trybie solo kasowane po 30 dniach; nauczyciel usuwa klasę wraz
  ze wszystkimi danymi jednym przyciskiem.

Aplikacja **nie wystawia ocen szkolnych** — mapa rozumienia służy do diagnozy.

---

## Katalog błędów

12 pozycji w `backend/catalog/`. Każda to plik JSON z fałszywą regułą Kuby, szablonem zadania
z losowanymi parametrami, poprawną regułą, kluczowymi ideami i pytaniami naprowadzającymi.
Przy starcie aplikacji SymPy sprawdza, że błędny krok naprawdę jest błędny.

| ID | Fałszywa reguła Kuby | Przykład |
| --- | --- | --- |
| K01 | (a + b)² = a² + b² | (x + 3)² = x² + 9 |
| K02 | mnożenie przez liczbę ujemną nie zmienia znaku nierówności | −2x > 6 ⇒ x > −3 |
| K03 | można dzielić przez niewiadomą | x² = 3x ⇒ x = 3 |
| K04 | √(a + b) = √a + √b | √(x² + 16) = x + 4 |
| K05 | w ułamku można skracać składniki | (x + 6) / 6 = x |
| K06 | x² = a ma jedno rozwiązanie | x² = 25 ⇒ x = 5 |
| K07 | kwadrat liczby ujemnej jest ujemny | f(−3) = −9 + 1 |
| K08 | log(a + b) = log a + log b | log(x + 10) = log x + 1 |
| K09 | +p% i potem −p% wraca do ceny wyjściowej | 100 zł → +20% → −20% |
| K10 | nie trzeba sprawdzać dziedziny | (x² − 4)/(x − 2) = 0 ⇒ x = ±2 |
| K11 | aᵐ · aⁿ = aᵐ·ⁿ | 2³ · 2⁴ = 2¹² |
| K12 | range(1, n) przechodzi przez całą listę | suma listy bez pierwszego elementu |

Dodanie trzynastej pozycji = jeden plik JSON. Autotest przy starcie i w CI pilnuje,
że nowa pozycja jest matematycznie poprawna.

---

## Dokumentacja

- [`docs/OPIS.md`](docs/OPIS.md) — opis funkcjonalności na jedną stronę (materiał zgłoszeniowy)
- [`docs/TESTY.md`](docs/TESTY.md) — jak odtworzyć wszystkie pomiary jakości
- [`docs/FILM.md`](docs/FILM.md) — scenariusz filmu 5-minutowego
- [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md) — diagramy i przepływ sesji

---

## Licencja

MIT — zgodna z niewyłączną licencją dla UwB z regulaminu konkursu. Szczegóły w [LICENSE](LICENSE).
Fonty Inter i Caveat na licencji OFL, KaTeX na MIT, ikony Lucide na ISC.
