# Naucz Kubę — instrukcja kompilacji

Dokument dla osoby, która chce zbudować aplikację ze źródeł. Wszystkie polecenia
zostały uruchomione na macOS 15 (Apple Silicon); w CI te same kroki przechodzą na
Ubuntu, Windows Server i macOS — patrz `.github/workflows/`.

---

## 1. Wymagania

| Narzędzie | Wersja | Sprawdzenie |
| --- | --- | --- |
| Python | 3.12 | `python3.12 --version` → `Python 3.12.13` |
| Node.js | 22 LTS | `node --version` → `v22.x` |
| npm | 10+ | `npm --version` |
| Git | dowolna | `git --version` |

Opcjonalnie: **Docker** (uruchomienie jednym poleceniem) i **Ollama** (tryb offline
z polskim modelem Bielik).

---

## 2. Pobranie kodu

```bash
git clone https://github.com/MichalKaronczyk/NauczKube.git
cd NauczKube
```

Jeśli pracujesz z archiwum `kod_zrodlowy.zip`, rozpakuj je i wejdź do katalogu:

```bash
unzip kod_zrodlowy.zip -d NauczKube
cd NauczKube
```

---

## 3. Frontend

Build trafia do `backend/static/`, skąd serwuje go FastAPI — dzięki temu całość
działa pod jednym adresem.

```bash
cd frontend
npm ci
npm run typecheck
npm run build
cd ..
```

---

## 4. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Do testów i lintera potrzebny jest dodatkowy zestaw:

```bash
pip install -r requirements-dev.txt
```

---

## 5. Konfiguracja

```bash
cp .env.example .env
```

Wszystkie zmienne są opisane w `.env.example`. **Żadna nie jest wymagana** —
bez kluczy API aplikacja działa na wbudowanych szablonach, a cała matematyka
(SymPy, kontrprzykłady, BKT) nie korzysta z modeli językowych.

Darmowy klucz Groq (bez karty): <https://console.groq.com/keys> → `GROQ_API_KEY`.

---

## 6. Uruchomienie w trybie deweloperskim

Dwa terminale:

```bash
# terminal 1 — backend z przeładowaniem
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

```bash
# terminal 2 — frontend z hot reloadem, proxy /api → :8000
cd frontend && npm run dev
```

Aplikacja: <http://localhost:5173>. Dokumentacja API: <http://localhost:8000/docs>.

Jeśli frontend jest już zbudowany (`npm run build`), wystarczy sam backend —
całość pod <http://localhost:8000>.

---

## 7. Testy

```bash
cd backend && source .venv/bin/activate
ruff check .
pytest -q
```

Wynik: **314 testów, ~7 s**. Testy jednostkowe nie wywołują zewnętrznego API —
fixture `_isolate_providers` zeruje łańcuch providerów, więc każde wywołanie AI
schodzi na tor offline.

Autotest katalogu błędów (ten sam, który uruchamia się przy starcie aplikacji):

```bash
python -c "from app.math.verify import selfcheck_catalog; r=selfcheck_catalog(); print(len(r),'sprawdzeń,',sum(1 for x in r if not x.ok),'niepoprawnych')"
```

Wynik: `57 sprawdzeń, 0 niepoprawnych`.

Testy end-to-end (wymagają zbudowanego frontendu i działającego backendu):

```bash
cd frontend
npx playwright install chromium webkit
npx playwright test
```

---

## 8. Wersja binarna (PyInstaller)

Najpierw zbuduj frontend (punkt 3) — spec pakuje katalog `backend/static`.

```bash
cd backend
source .venv/bin/activate
pip install pyinstaller
pyinstaller naucz-kube.spec --noconfirm
```

Wynik: `backend/dist/naucz-kube` (na Windows `naucz-kube.exe`), ok. 38 MB.
Plik uruchamia serwer na `127.0.0.1:8000` i sam otwiera przeglądarkę.
Baza SQLite powstaje w katalogu danych użytkownika (patrz `app/paths.py`).

**PyInstaller nie kompiluje skrośnie** — plik `.exe` dla Windows musi powstać na
Windows. Gotowy workflow buduje wszystkie trzy platformy naraz:

```bash
gh workflow run build-binary.yml --ref main
gh run download <ID_PRZEBIEGU> --dir dist-release
```

Albo ręcznie: zakładka **Actions → „Wersja binarna" → Run workflow**.
Każdy build kończy się testem dymnym — binarka musi wstać i odpowiedzieć
na `/api/health`, inaczej przebieg pada.

---

## 9. Docker

```bash
cp .env.example .env
docker compose up
```

Aplikacja: <http://localhost:8000>. Obraz buduje frontend i backend w jednym
kroku (`Dockerfile`, build wieloetapowy).

Tryb offline z Bielikiem:

```bash
ollama pull SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M
echo "OFFLINE_ONLY=true" >> .env
docker compose --profile offline up
```

---

## 10. Najczęstsze problemy

| Objaw | Przyczyna i rozwiązanie |
| --- | --- |
| `ModuleNotFoundError: app` | Polecenia backendu uruchamiaj z katalogu `backend/`, przy aktywnym `.venv`. |
| Pusta strona pod `:8000` | Brak `backend/static/` — wykonaj `npm run build` we frontendzie. |
| `address already in use` | Port 8000 zajęty: `PORT=8010 uvicorn app.main:app --port 8010`. |
| PyInstaller: `Failed to execute script` | Build frontendu wykonany po `pyinstaller` — powtórz w kolejności: `npm run build`, potem `pyinstaller`. |
| Playwright: brak przeglądarek | `npx playwright install chromium webkit`. |
