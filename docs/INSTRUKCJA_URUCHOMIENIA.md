# Naucz Kubę — instrukcja uruchomienia

Aplikacja nie wymaga instalacji. To jeden plik, który uruchamia serwer na Twoim
komputerze i sam otwiera przeglądarkę. Nic nie trzeba konfigurować, żeby zacząć.

---

## 1. Pobranie i rozpakowanie

1. Pobierz plik `NauczKube_windows.zip` (albo `NauczKube_macos.zip` / `NauczKube_linux.zip`).
2. Kliknij go prawym przyciskiem → **Wyodrębnij wszystkie** (Windows) lub dwukrotnie (macOS).
3. **Uruchamiaj aplikację dopiero po rozpakowaniu.** Uruchomiona bezpośrednio z archiwum
   nie będzie działać poprawnie.

---

## 2. Uruchomienie

### Windows

Kliknij dwukrotnie **`NauczKube.exe`**.

Przy pierwszym uruchomieniu Windows pokaże niebieskie okno
**„System Windows ochronił Twój komputer”** (SmartScreen). To standardowe ostrzeżenie
dla programów bez płatnego podpisu cyfrowego — nie oznacza wirusa.

1. Kliknij **„Więcej informacji”**.
2. Kliknij przycisk **„Uruchom mimo to”**.

Windows Defender może dodatkowo skanować plik przez kilkanaście sekund przy pierwszym
starcie. To normalne — aplikacja waży ok. 40 MB.

### macOS

Plik nie jest podpisany certyfikatem Apple, więc dwukrotne kliknięcie pokaże komunikat
**„Nie można otworzyć, ponieważ pochodzi od niezidentyfikowanego dewelopera”**.

**Sposób 1 (zalecany):** kliknij plik `naucz-kube` **prawym przyciskiem** (lub Ctrl + klik)
→ **„Otwórz”** → w oknie z ostrzeżeniem ponownie **„Otwórz”**. System zapamięta tę zgodę
i następnym razem wystarczy zwykłe kliknięcie.

**Sposób 2 (Terminal):** jeśli macOS nadal blokuje plik (np. komunikat
„plik jest uszkodzony”), zdejmij atrybut kwarantanny:

```bash
xattr -d com.apple.quarantine ./naucz-kube
chmod +x ./naucz-kube
./naucz-kube
```

W nowszych wersjach macOS zgodę można też wydać w **Ustawienia systemowe → Prywatność
i ochrona → Ochrona**, przycisk **„Otwórz mimo to”** (pojawia się po pierwszej
nieudanej próbie).

### Linux

```bash
chmod +x ./naucz-kube
./naucz-kube
```

---

## 3. Co się dzieje po uruchomieniu

Otworzy się czarne okno konsoli (nie zamykaj go — to działający serwer), a po około
2 sekundach domyślna przeglądarka z adresem:

```
http://127.0.0.1:8000
```

Jeśli przeglądarka nie otworzy się sama, wpisz ten adres ręcznie. Działa Chrome, Edge,
Firefox i Safari.

**Zamykanie:** zamknij okno konsoli albo naciśnij w nim `Ctrl + C`.

---

## 4. Klucz API — czy jest potrzebny?

**Nie jest potrzebny, żeby obejrzeć i przetestować całą aplikację.** Bez klucza Kuba
mówi z wbudowanych szablonów po polsku, a wyjaśnienia ocenia deterministyczna
heurystyka. Cała matematyka — SymPy, kontrprzykłady, weryfikacja poprawek i mapa
rozumienia — działa identycznie, bo w ogóle nie korzysta z modeli językowych.

Z kluczem Kuba mówi swobodniej. Darmowy klucz Groq (bez karty płatniczej) zakłada się
w 2 minuty:

1. Wejdź na <https://console.groq.com/keys> i załóż konto.
2. Kliknij **Create API Key**, skopiuj klucz (zaczyna się od `gsk_`).
3. Uruchom aplikację ze zmienną środowiskową:

   **Windows (PowerShell):**
   ```powershell
   $env:GROQ_API_KEY = "gsk_tutaj_wklej_klucz"
   .\NauczKube.exe
   ```

   **macOS / Linux:**
   ```bash
   GROQ_API_KEY="gsk_tutaj_wklej_klucz" ./naucz-kube
   ```

Klucz jest czytany **wyłącznie po stronie serwera** i nigdy nie trafia do przeglądarki.

### Tryb offline (dane zostają w szkole)

Aplikacja potrafi działać na polskim modelu **Bielik** uruchomionym lokalnie, bez
internetu. Wymaga zainstalowanej [Ollamy](https://ollama.com):

```bash
ollama pull SpeakLeash/bielik-11b-v3.1-instruct:Q4_K_M
OFFLINE_ONLY=true ./naucz-kube
```

---

## 5. Gdzie zapisują się dane

Baza SQLite powstaje w katalogu danych użytkownika, nie obok pliku:

| System | Lokalizacja |
| --- | --- |
| Windows | `%LOCALAPPDATA%\NauczKube\naucz_kube.db` |
| macOS | `~/Library/Application Support/NauczKube/naucz_kube.db` |
| Linux | `~/.local/share/NauczKube/naucz_kube.db` |

Aplikacja **nie zbiera danych osobowych** — nie ma kont, e-maili ani nazwisk, tylko
pseudonim wybrany przez ucznia. Nagranie głosu nie jest zapisywane: idzie do
transkrypcji i jest kasowane.

Żeby usunąć wszystkie dane, skasuj ten jeden plik `.db`.

---

## 6. Rozwiązywanie problemów

### Port 8000 jest zajęty

W konsoli pojawi się `address already in use`. Uruchom aplikację na innym porcie:

**Windows (PowerShell):**
```powershell
$env:PORT = "8010"
.\NauczKube.exe
```

**macOS / Linux:**
```bash
PORT=8010 ./naucz-kube
```

Następnie otwórz `http://127.0.0.1:8010`.

### Brak internetu

Aplikacja działa dalej. Kuba przechodzi na wbudowane szablony, a wyjaśnienia ocenia
heurystyka. Zadania, sprawdzanie błędów i mapa rozumienia działają bez zmian.

### Przekroczony limit darmowego API

Komunikat o błędzie providera albo zauważalne spowolnienie odpowiedzi. Gateway sam
przechodzi na kolejnego dostawcę, a gdy wszystkie są wyczerpane — na tryb wbudowany.
Nic się nie zatrzyma. Dzienne limity Groq resetują się o północy UTC.

Aktualny stan providerów i limitów widać pod adresem:
```
http://127.0.0.1:8000/api/health
```

### Przeglądarka pokazuje pustą stronę

Odśwież stronę (`Ctrl + R` / `Cmd + R`). Jeśli nie pomoże, sprawdź, czy okno konsoli
nadal działa — zamknięcie go zatrzymuje serwer.

### Strona nie otwiera się wcale

Upewnij się, że używasz adresu `http://127.0.0.1:8000`, a nie `https://`. Aplikacja
działa lokalnie, bez szyfrowania — nic nie wychodzi poza Twój komputer.
