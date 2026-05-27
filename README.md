# KCK-4I10-Cyber-trener
  Ćwiczenie „dipy tyłem na krześle” zostało wybrane jako punkt wyjścia do stworzenia systemu analizy ruchu (e-trenera). Jest to ćwiczenie wykorzystujące masę własnego ciała, które angażuje głównie mięśnie trójgłowe ramienia, a także mięśnie barków i klatki piersiowej. 

  Jego główną zaletą jest prostota: nie wymaga specjalistycznego sprzętu i może być wykonywane praktycznie wszędzie. Jednocześnie ta prostota stanowi wyzwanie projektowe, ponieważ łatwość wykonania utrudnia stworzenie zaawansowanego systemu detekcji błędów przy użyciu jednej kamery. 

  Celem projektu jest opracowanie systemu wspomagającego użytkownika w poprawnym wykonywaniu ćwiczenia poprzez: 

1. Analizę pozycji ciała, 

2. Wykrywanie błędów technicznych, 

3. Dostarczanie informacji zwrotnej w czasie rzeczywistym. 

  Użytkownik opiera dłonie na krawędzi krzesła za plecami, opuszcza ciało poprzez zginanie łokci, a następnie wraca do pozycji wyjściowej poprzez ich wyprost. 

  Najczęstsze błędy, które powinien wykrywać system: 

1. Zbyt duże oddalenie pleców od krzesła (utrata stabilizacji)  

2. Rozchodzenie się łokci na boki zamiast prowadzenia ich do tyłu  

3. Zbyt płytki zakres ruchu (brak zejścia do poziomu równoległego ramion)  

4. Przeprost w łokciach przy powrocie  

5. Unoszenie barków do góry (napięcie szyi)  

6. Brak kontroli ruchu (ruch zbyt szybki / szarpany)  

7. Niewłaściwe ustawienie nóg (niestabilna pozycja)

   Scenariusz powodzenia:
  1. Użytkownik poprawnie ustawia kamerę oraz przyjmuje pozycję startową.
  2. System wykrywa sylwetkę i rozpoczyna analizę ruchu.
  3. Użytkownik wykonuje ćwiczenie:
    - plecy pozostają blisko krzesła,
    - łokcie prowadzone są do tyłu,
    - zakres ruchu jest odpowiedni,
    - ruch wykonywany jest płynnie.
  4. System analizuje ruch i oznacza powtórzenia jako poprawne.
Rezultat:
Użytkownik otrzymuje informację o poprawnym wykonaniu ćwiczenia oraz liczbę poprawnych powtórzeń.

    Scenariusz niepowodzenia:
  1. Kamera jest ustawiona niepoprawnie lub sylwetka użytkownika znajduje się częściowo poza kadrem.
  2. System nie może dokładnie wykryć pozycji stawów.
  3. Analiza ruchu staje się niedokładna i pojawiają się błędne odczyty.
Rezultat:
  System nie jest w stanie poprawnie ocenić ćwiczenia.
Reakcja systemu:
  Wyświetlany jest komunikat:
    -„Ustaw całą sylwetkę w kadrze”
    -„Popraw ustawienie kamery lub oświetlenie”

  Mimo że ćwiczenie jest stosunkowo proste, stanowi dobry punkt startowy do budowy systemu analizy ruchu. Pozwala skupić się na podstawowych aspektach detekcji pozycji ciała oraz identyfikacji błędów, bez konieczności obsługi skomplikowanych sekwencji ruchowych. 

  Jednocześnie jego prostota wymaga dokładniejszego podejścia do analizy jakości ruchu, co czyni je dobrym przypadkiem testowym. 



# Instrukcja uruchomienia projektu

Ten projekt wymaga Pythona w wersji 3.x oraz biblioteki PySide6 (Qt). Postępuj zgodnie z poniższymi krokami, aby poprawnie skonfigurować środowisko i uruchomić aplikację.

## 🚀 Szybki start

Wymagane jest posiadanie zainstalowanego Pythona oraz systemu zarządzania pakietami `pip`.

### 1. Pobierz projekt
Sklonuj repozytorium lub pobierz pliki projektu na swój dysk.

### 2. Utwórz wirtualne środowisko (venv)
Otwórz terminal w głównym folderze projektu i wpisz:
    python3 -m venv venv

### 3.Aktywuj środowisko wirtualne

W zależności od Twojego systemu operacyjnego uruchom odpowiednią komendę:
*   **Linux / macOS:**            source venv/bin/activate

*   **Windows (Command Prompt):** venv\Scripts\activate

*   **Windows (PowerShell):**     .\venv\Scripts\activate

*Po aktywacji powinieneś zobaczyć oznaczenie `(venv)` na początku linii w terminalu.*

### 4. Zainstaluj wymagane pakiety
Zainstaluj automatycznie wszystkie zależności zapisane w pliku konfiguracyjnym:
    pip install -r requirements.txt

### 5. Wylaczenie srodowiska
    

# Instrukcja dla Deweloperów (Praca nad Projektem)

Witaj w zespole! Aby zachować porządek w kodzie i unikać konfliktów między globalnymi pakietami (np. Conda `base`), zawsze pracujemy wewnątrz izolowanego środowiska wirtualnego.

## 🛠️ Codzienna praca z kodem

Zanim zaczniesz pisać kod lub uruchomisz edytor (np. VS Code, PyCharm), **zawsze upewnij się, że Twoje środowisko `venv` jest aktywne**.

## Dodawanie nowych bibliotek (Zasada czystego requirements.txt)

Jeśli w trakcie pisania kodu zaimportujesz nową zewnętrzną bibliotekę (np. do obsługi bazy danych czy wykresów):

*   Zainstaluj ją wewnątrz aktywnego venv:
       pip install nazwa_pakietu

*   Zaktualizuj plik z zależnościami, aby inni deweloperzy oraz użytkownicy również go otrzymali:
        pip freeze > requirements.txt

*   Zgłoś plik requirements.txt do Gita razem ze swoimi zmianami w kodzie.

# Czego NIE robić (Ważne!)

*   Nigdy nie instaluj pakietów globalnie (base) podczas pracy nad tym projektem. Jeśli zapomnisz aktywować venv, polecenie pip freeze wyeksportuje setki Twoich prywatnych pakietów do pliku projektu.

*   Nigdy nie dodawaj folderu venv/ do repozytorium Git. Środowisko wirtualne każdego programisty zawiera unikalne ścieżki systemowe. Folder venv/ powinien być zawsze dopisany do pliku .gitignore.

# Struktura Projektu

*  menu.py - Główny plik wejściowy aplikacji.

*   requirements.txt - Lista zależności (generowana automatycznie).
 
*   venv/ - Lokalny folder środowiska (Ignorowany przez Git)

