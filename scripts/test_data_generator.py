import json
import random
from datetime import datetime, timedelta


def generate_workout_data():
    # Ustawiamy punkt końcowy na dzisiejszą datę
    end_date = datetime(2026, 6, 13, 18, 0, 0)
    # Rozpoczynamy 4 miesiące wcześniej (około 120 dni)
    current_date = end_date - timedelta(days=120)

    series_list = []

    # Parametry początkowe dla progresu liniowego
    base_total_reps = 8  # zaczynamy od 8 powtórzeń w serii
    base_correct_ratio = 0.65  # zaczynamy od ~65% poprawnych powtórzeń

    workout_index = 0

    while current_date <= end_date:
        workout_index += 1

        # Co drugi trening (gdy workout_index jest parzysty) lekko zwiększamy parametry
        if workout_index % 2 == 0:
            base_total_reps += random.choice([0, 1])  # powolny wzrost powtórzeń
            base_correct_ratio = min(
                0.95, base_correct_ratio + 0.012
            )  # wzrost jakości max do 95%

        # Liczba powtórzeń w tej serii (z lekką losowością wokół bazy)
        total_reps = int(base_total_reps + random.choice([-1, 0, 1]))
        total_reps = max(5, total_reps)  # zabezpieczenie dolne

        # Obliczanie poprawnych powtórzeń na podstawie aktualnej jakości
        correct_reps = round(total_reps * base_correct_ratio)
        correct_reps = min(total_reps, max(0, correct_reps))
        faulty_reps = total_reps - correct_reps

        # Czas trwania serii powiązany z liczbą powtórzeń (średnio 3-4 sekundy na powtórzenie)
        duration = total_reps * 3 + random.randint(5, 12)

        # Generowanie powtórzeń (lista struktur)
        repetitions = []

        # Dodajemy poprawne powtórzenia
        for _ in range(correct_reps):
            repetitions.append(
                {
                    "speed": round(random.uniform(2.0, 2.8), 1),
                    "quality": "Correct",
                    "errors": {
                        "too_narrow": False,
                        "too_wide": False,
                        "legs_bent": False,
                        "bad_torso_angle": False,
                    },
                }
            )

        # Dodajemy błędne powtórzenia (z losowymi błędami)
        for _ in range(faulty_reps):
            # Losujemy, które błędy się pojawiły
            legs_bent = random.choice([True, False])
            bad_torso_angle = (
                not legs_bent if not legs_bent else random.choice([True, False])
            )
            too_wide = (
                random.choice([True, False])
                if not (legs_bent or bad_torso_angle)
                else False
            )
            too_narrow = False if too_wide else random.choice([True, False])

            repetitions.append(
                {
                    "speed": round(
                        random.uniform(3.0, 4.5), 1
                    ),  # wadliwe zazwyczaj są za wolne/za szybkie
                    "quality": "Faulty",
                    "errors": {
                        "too_narrow": too_narrow,
                        "too_wide": too_wide,
                        "legs_bent": legs_bent,
                        "bad_torso_angle": bad_torso_angle,
                    },
                }
            )

        # Mieszamy powtórzenia, żeby nie były idealnie pogrupowane
        random.shuffle(repetitions)

        # Tworzenie pojedynczego obiektu serii
        hour = random.randint(8, 20)
        minute = random.randint(0, 59)
        exec_datetime = current_date.replace(hour=hour, minute=minute)

        seria = {
            "metadata": {
                "date": exec_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "location": random.choice(["Siłownia", "Dom", "Park"]),
                "duration_seconds": duration,
            },
            "repetitions": repetitions,
        }

        series_list.append(seria)

        # Odstęp do następnego treningu: średnio 3 dni (losowo od 2 do 4 dni)
        current_date += timedelta(days=random.randint(2, 4))

    # Zapis do pliku JSON
    with open("treningi_4_miesiace.json", "w", encoding="utf-8") as f:
        json.dump(series_list, f, indent=2, ensure_ascii=False)

    print(f"Wygenerowano {len(series_list)} serii w pliku 'treningi_4_miesiace.json'")


if __name__ == "__main__":
    generate_workout_data()
