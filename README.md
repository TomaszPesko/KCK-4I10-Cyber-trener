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

  Mimo że ćwiczenie jest stosunkowo proste, stanowi dobry punkt startowy do budowy systemu analizy ruchu. Pozwala skupić się na podstawowych aspektach detekcji pozycji ciała oraz identyfikacji błędów, bez konieczności obsługi skomplikowanych sekwencji ruchowych. 

  Jednocześnie jego prostota wymaga dokładniejszego podejścia do analizy jakości ruchu, co czyni je dobrym przypadkiem testowym. 
