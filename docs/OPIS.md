# Naucz Kubę — opis funkcjonalności

*Konkurs „Sztuczna inteligencja wśród nas”, Wydział Informatyki UwB*

## 1. Pomysł i problem

Popularne AI-tutory rozwiązują zadania **za** ucznia, więc uczeń przestaje myśleć.
**Naucz Kubę** odwraca role: to uczeń uczy AI. Kuba, wirtualny kolega z klasy, rozwiązuje
zadanie z matematyki i popełnia jeden typowy błąd w rozumowaniu — uczeń musi go znaleźć
i wytłumaczyć. Podstawa: efekt protegowanego (learning by teaching) — tłumacząc komuś,
uczeń porządkuje własną wiedzę.

## 2. Jak działa sesja (5 kroków)

1. **Kuba pisze rozwiązanie** na tablicy, linijka po linijce, pismem odręcznym, i prosi
   o sprawdzenie: „wynik wyszedł mi dziwny”. Przy pierwszym wejściu uczeń dostaje krótką
   kartę „jak to działa”, a nad tablicą przez cały czas widnieje pasek kroków z instrukcją
   na teraz.
2. **Uczeń zakreśla rysikiem** linijkę z błędem. Zakreślenie jest mapowane na numer linijki
   geometrycznie (przecięcie obrysów), bez udziału AI. Przy nietrafieniu Kuba dopytuje,
   a po dwóch próbach lub 90 sekundach bez ruchu włącza się drabinka podpowiedzi:
   zawężenie → test liczbowy z SymPy → wskazanie linijki z pytaniem. Poprawna reguła
   nigdy nie pada wprost.
3. **Kuba się broni** swoim błędnym przekonaniem. Uczeń tłumaczy — głosem, pismem odręcznym
   lub z klawiatury. Ewaluator sprawdza, czy wyjaśnienie zawiera wszystkie wymagane
   kluczowe idee z katalogu; przy brakach Kuba zadaje naiwne pytanie celujące w pierwszą lukę.
4. **Kuba rozumie**: streszcza regułę własnymi słowami i poprawia błędną linijkę.
5. **Zadanie transferowe**: Kuba rozwiązuje nowe zadanie z tego samego szablonu i w ok. 30%
   przypadków znów się myli. Uczeń musi je ocenić — to sprawdza czujność, a nie zgadywanie.
   Wynik aktualizuje mapę rozumienia.

## 3. Wykorzystanie AI (6 elementów)

1. **LLM-aktor** — persona Kuby, który szczerze wierzy w jeden błąd. Orkiestrator (maszyna
   stanów w Pythonie) wybiera dyrektywę, a model tylko dobiera słowa. Kod wykrywa
   i blokuje ujawnienie reguły przed czasem.
2. **LLM-oceniający** — ewaluator wyjaśnień w temperaturze 0. Dla każdej kluczowej idei
   musi podać dosłowny cytat z wypowiedzi ucznia; **kod weryfikuje cytat** (podobieństwo
   ≥ 0,85). Brak dowodu = idea niezaliczona, niezależnie od tego, co twierdzi model.
3. **Rozpoznawanie pisma** (model vision) — odręczna poprawka ucznia → LaTeX, z twardym
   zakazem „naprawiania” błędu i potwierdzeniem odczytu przez ucznia.
4. **Rozpoznawanie mowy** (Whisper) — wyjaśnienie głosem; uczeń widzi transkrypcję
   i może ją poprawić przed wysłaniem.
5. **Weryfikacja symboliczna (SymPy)** — jedyne źródło prawdy o matematyce: potwierdza,
   że błędny krok jest błędny, sprawdza poprawkę ucznia i generuje kontrprzykłady liczbowe
   do podpowiedzi.
6. **Model wiedzy (Bayesian Knowledge Tracing)** — dla każdej pary uczeń × błąd liczone jest
   P(L), prawdopodobieństwo opanowania; próg opanowania 0,95.

**Zasada nadrzędna: kod decyduje, CO robi Kuba; LLM decyduje tylko, JAK to powie.**
Dzięki temu Kuba nie poddaje się za wcześnie, nie halucynuje matematyki i nie da się go
przekonać prośbą „po prostu powiedz, co jest źle”.

## 4. Dla nauczyciela

Nauczyciel tworzy klasę, dostaje 6-znakowy kod dla uczniów i PIN do panelu. W panelu widzi
mapę ciepła uczniowie × błędy K01–K12 (odcień komórki = P(L)), listę „czego klasa nie wyłapuje”,
filtr tematów i eksport CSV. Widzi **mapę opanowania, nie treść rozmów uczniów**. Jednym
przyciskiem usuwa klasę razem ze wszystkimi danymi. Aplikacja nie wystawia ocen szkolnych.

## 5. Bezpieczeństwo i prywatność

Nie zbieramy danych osobowych — nie ma kont, e-maili, nazwisk ani wieku, tylko pseudonim
wybrany przez ucznia; do zewnętrznego API nie trafia ani pseudonim, ani kod klasy, a e-maile,
telefony i numery PESEL są wycinane z tekstu przed wysłaniem. Nagranie głosu jest kasowane
zaraz po transkrypcji, klucze API zostają na serwerze, PIN nauczyciela jest hashowany (argon2),
a tryb „tylko offline” z polskim modelem Bielik pozwala zostawić wszystkie dane w szkole.
Jeśli moderacja wykryje sygnały przemocy lub samookaleczenia, Kuba wychodzi z roli, sesja się
zatrzymuje i pojawia się karta z numerem 116 111 — treść nie trafia do panelu nauczyciela.

## 6. Technologie i uruchomienie

React 19 + TypeScript (tablica: Pointer Events z naciskiem rysika, perfect-freehand,
pismo Kuby: Caveat + KaTeX), FastAPI + Python 3.12 (SymPy, SQLite, Pydantic), darmowe API
zgodne z OpenAI (Groq → Mistral → OpenRouter → lokalny Bielik przez Ollamę).
Uruchomienie jednym poleceniem `docker compose up` albo jednym plikiem `naucz-kube.exe`,
który sam otwiera przeglądarkę pod `localhost:8000`; aplikacja działa też bez żadnego klucza
API i bez internetu.

---

**Wyniki własnych testów** (308 testów jednostkowych + 30 E2E): autotest katalogu SymPy 100%,
weryfikator poprawek 50/50, ewaluator 98% zgodności na 60 oznaczonych wyjaśnieniach
przy zerze przyjętych błędnych, szczelność persony 0 ujawnień na 150 próbach,
pełna sesja E2E przechodzi w Chrome i Safari (iPad). Kod na licencji MIT.
