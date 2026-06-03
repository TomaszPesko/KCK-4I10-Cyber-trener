​ Opis projektu „Cyber-Trener”
Cyber-Trener jest samodzielną aplikacją (stand-alone), której zadaniem jest wspomaganie użytkownika podczas wykonywania ćwiczenia „dipy tyłem na krześle” (bench dips). System wykorzystuje analizę obrazu z jednej lub dwóch kamer w celu rozpoznawania pozycji ciała, monitorowania przebiegu ruchu oraz wykrywania błędów technicznych podczas wykonywania ćwiczenia.
Wybrane ćwiczenie angażuje głównie mięśnie trójgłowe ramienia, mięśnie barków oraz klatki piersiowej. Jego zaletą jest możliwość wykonywania bez specjalistycznego sprzętu, jednak ze względu na pozycję ćwiczącego – ustawionego tyłem do kierunku ruchu – użytkownik nie jest w stanie na bieżąco kontrolować wielu istotnych elementów techniki. Powoduje to zwiększone ryzyko utrwalania błędnych wzorców ruchowych oraz przeciążeń stawów barkowych i łokciowych.
System Cyber-Trener ma za zadanie analizować wykonywane ruchy, wykrywać najczęściej występujące błędy oraz przekazywać użytkownikowi informacje zwrotne w czasie rzeczywistym. Program może pracować w konfiguracji z jedną kamerą (widok boczny) lub dwiema kamerami (widok boczny i przedni), co pozwala na dokładniejszą ocenę pozycji ciała i jakości wykonywanego ruchu.
Do błędów wykrywanych przez system należą między innymi:
    • zbyt duże oddalenie pleców od krzesła, 
    • rozchodzenie się łokci na boki, 
    • zbyt płytki zakres ruchu, 
    • unoszenie barków do góry, niepoprawna postawa
    • nieprawidłowe ustawienie nóg wpływające na stabilność pozycji. 
Po zakończeniu ćwiczenia użytkownik otrzymuje podsumowanie zawierające liczbę wykonanych powtórzeń oraz listę wykrytych błędów wraz z informacją, podczas których powtórzeń wystąpiły.
​ Aktorzy systemu
​ Użytkownik
Osoba wykonująca ćwiczenie przed kamerą. Korzysta z aplikacji w celu monitorowania poprawności techniki oraz uzyskania informacji zwrotnej dotyczącej wykonywanego ćwiczenia.
​ Administrator
Administrator nie jest częścią procesu treningowego. Jest to osoba zewnętrzna odpowiedzialna za konfigurację i utrzymanie aplikacji stand-alone. Do jego zadań należy dostarczenie poprawnego instolatora programu, aktualizacja modeli analizy ruchu, konfiguracja opcji dołączania kamer oraz plików wideo oraz testowanie poprawności działania systemu.
​ 
​ Diagram przypadków użycia (opis tekstowy)
System Cyber-Trener udostępnia następujące przypadki użycia:
​ Dla użytkownika
    • Uruchomienie aplikacji 
    • Rozpoczęcie sesji treningowej 
    • Wykrycie sylwetki użytkownika 
    • Kalibracja pozycji startowej 
    • Wykonywanie ćwiczenia 
    • Otrzymywanie wskazówek w czasie rzeczywistym 
    • Liczenie poprawnych powtórzeń 
    • Przegląd wyników treningu 
    • Zakończenie sesji 
​ Dla administratora
    • Instalacja i wdrożenie aplikacji 
    • Konfiguracja źródeł obrazu (kamer oraz plików wideo) 
    • Konfiguracja parametrów analizy ruchu 
    • Aktualizacja modeli analizy ruchu 
    • Testowanie poprawności działania aplikacji 

​ Opisy przypadków użycia
​ PU1 – Uruchomienie aplikacji
Cel: Uruchomienie systemu Cyber-Trener.
Aktor: Użytkownik
Warunki początkowe: Program jest zainstalowany na komputerze.
Przebieg główny:
    1. Użytkownik uruchamia aplikację. 
    2. System inicjalizuje moduły analizy obrazu. 
    3. System uruchamia kamerę. 
    4. Następuje przejście do wykrywania użytkownika. 
Rezultat: System jest gotowy do rozpoczęcia treningu.

​ PU2 – Wykrycie użytkownika
Cel: Zlokalizowanie osoby znajdującej się przed kamerą.
Aktor: Użytkownik
Warunki początkowe: Kamera jest aktywna.
Przebieg główny:
    1. System analizuje obraz z kamery. 
    2. Wykrywana jest sylwetka użytkownika. 
    3. Użytkownik przyjmuje pozycję startową. 
    4. System rozpoczyna monitorowanie ćwiczenia. 
Rezultat: Rozpoczyna się analiza ruchu.

​ PU3 – Wykonywanie ćwiczenia
Cel: Analiza poprawności wykonywanych dipów.
Aktor: Użytkownik
Warunki początkowe: Użytkownik został poprawnie wykryty.
Przebieg główny:
    1. Użytkownik wykonuje ruch opuszczania ciała. 
    2. System śledzi położenie stawów. 
    3. Analizowana jest trajektoria ruchu. 
    4. System wykrywa ewentualne błędy. 
    5. Po zakończeniu pełnego cyklu ruchu naliczane jest powtórzenie. 
Rezultat: Powtórzenie zostaje sklasyfikowane jako poprawne lub błędne.

​ PU4 – Generowanie informacji zwrotnej
Cel: Przekazanie użytkownikowi wskazówek dotyczących techniki.
Aktor: Użytkownik
Warunki początkowe: W trakcie analizy wykryto nieprawidłowość.
Przebieg główny:
    1. System identyfikuje błąd techniczny. 
    2. Wyświetlany jest odpowiedni komunikat. 
    3. Użytkownik koryguje swoją pozycję. 
    4. Analiza jest kontynuowana. 
Rezultat: Poprawa jakości wykonywanego ćwiczenia.

​ PU5 – Przegląd wyników
Cel: Zapoznanie użytkownika z wynikami treningu.
Aktor: Użytkownik
Warunki początkowe: Sesja treningowa została zakończona.
Przebieg główny:
    1. System zatrzymuje analizę ruchu. 
    2. Zliczane są wszystkie wykonane powtórzenia. 
    3. Tworzona jest lista wykrytych błędów. 
    4. Wyświetlane jest podsumowanie treningu. 
Rezultat: Użytkownik otrzymuje raport z wykonanej sesji.

​ Scenariusz powodzenia
Użytkownik uruchamia aplikację i ustawia kamerę w odpowiedniej pozycji. Następnie przyjmuje pozycję startową przy krześle. System poprawnie wykrywa sylwetkę oraz położenie kluczowych punktów ciała i rozpoczyna analizę ruchu.
Podczas wykonywania ćwiczenia użytkownik utrzymuje plecy blisko krzesła, prowadzi łokcie do tyłu, wykonuje odpowiednio głębokie zejście oraz zachowuje płynność ruchu. System nie wykrywa istotnych błędów technicznych i uznaje kolejne powtórzenia za poprawne.
Po zakończeniu ćwiczenia użytkownik wydaje komendę zakończenia lub przyjmuje zdefiniowaną pozycję końcową. System generuje raport zawierający liczbę poprawnie wykonanych powtórzeń oraz informację o prawidłowej technice wykonania ćwiczenia.

​ Scenariusz niepowodzenia
Użytkownik uruchamia aplikację, jednak kamera została ustawiona nieprawidłowo lub część sylwetki znajduje się poza kadrem. W wyniku tego system nie jest w stanie poprawnie wykryć wszystkich punktów charakterystycznych ciała.
Analiza ruchu staje się niedokładna, co uniemożliwia prawidłową ocenę techniki ćwiczenia. System wykrywa problem z jakością obrazu i wyświetla komunikat informujący o konieczności poprawy warunków nagrywania.
Użytkownik otrzymuje komunikaty:
    • „Ustaw całą sylwetkę w kadrze”. 
    • „Popraw ustawienie kamery”. 
    • „Zwiększ oświetlenie pomieszczenia”. 
Do czasu usunięcia problemu analiza ruchu zostaje wstrzymana lub oznaczona jako niewiarygodna.

​ Scenariusze alternatywne
​ SA1 – Wykrycie błędnej techniki
    1. Użytkownik rozpoczyna wykonywanie ćwiczenia. 
    2. System wykrywa rozchodzenie się łokci na boki. 
    3. Wyświetlany zostaje komunikat „Prowadź łokcie bliżej ciała”. 
    4. Użytkownik koryguje ruch. 
    5. Analiza jest kontynuowana. 
​ SA2 – Zbyt mały zakres ruchu
    1. Użytkownik wykonuje powtórzenie. 
    2. System stwierdza niewystarczające obniżenie ciała. 
    3. Powtórzenie zostaje oznaczone jako niepełne. 
    4. Wyświetlana jest informacja „Zwiększ zakres ruchu”. 
​ SA3 – Utrata użytkownika z kadru
    1. Podczas ćwiczenia część sylwetki opuszcza obszar widoczny dla kamery. 
    2. System traci możliwość śledzenia wybranych punktów ciała. 
    3. Analiza zostaje chwilowo zatrzymana. 
    4. Użytkownik wraca do pełnej widoczności. 
    5. System wznawia monitorowanie ćwiczenia. 

​ Administrator systemu
W projekcie Cyber-Trener administrator nie uczestniczy bezpośrednio w treningu użytkownika. Jego rola ogranicza się do czynności technicznych związanych z przygotowaniem i utrzymaniem aplikacji. Administrator może skonfigurować źródła obrazu, ustawić parametry działania algorytmów, przeprowadzić testy poprawności działania oraz udostępniać nowe wersje systemu i reagować na błędy i problemy użytkownika. Ponieważ aplikacja działa lokalnie jako program stand-alone, administrator jest traktowany jako aktor zewnętrzny wobec głównego procesu analizy ćwiczenia.
