import json
import random
from datetime import datetime, timedelta


def generate_parameterized_workout_data(
    profile_type="linear_progress", output_filename="workout_history.json"
):
    """Generates tailored tracking profiles to mock real trainer progress variables.

    Supported profile_types:
      - 'linear_progress': Smooth continuous improvements in volume and accuracy.
      - 'fatigue_regression': Initial peaks followed by drop-offs in quality.
      - 'plateau': Rapid early adaptation followed by complete stabilization.
    """
    # Define time boundaries matching project timelines
    end_date = datetime(2026, 6, 13, 18, 0, 0)
    current_date = end_date - timedelta(days=120)

    series_list = []
    workout_day_index = 0

    # Configure baseline criteria variables per profile type
    if profile_type == "linear_progress":
        base_total_reps = 8
        base_correct_ratio = 0.60
    elif profile_type == "fatigue_regression":
        base_total_reps = 12
        base_correct_ratio = 0.85
    elif profile_type == "plateau":
        base_total_reps = 6
        base_correct_ratio = 0.50
    else:
        # Fallback profile setup
        base_total_reps = 8
        base_correct_ratio = 0.70

    while current_date <= end_date:
        workout_day_index += 1

        # Profile tracking adjustment mechanics (applied once per day)
        if profile_type == "linear_progress":
            if workout_day_index % 2 == 0:
                base_total_reps += random.choice([0, 1])
                base_correct_ratio = min(0.96, base_correct_ratio + 0.015)

        elif profile_type == "fatigue_regression":
            if workout_day_index > 15:
                # Fatigue accumulation begins dropping accuracy margins
                base_total_reps = max(6, base_total_reps - random.choice([0, 0, 1]))
                base_correct_ratio = max(0.40, base_correct_ratio - 0.02)

        elif profile_type == "plateau":
            if workout_day_index < 12:
                # Early fast tracking adaptation gains
                if workout_day_index % 2 == 0:
                    base_total_reps += 1
                    base_correct_ratio = min(0.80, base_correct_ratio + 0.04)
            # Beyond index 12, values freeze to simulate a plateau

        # MODYFIKACJA 1: Generowanie kilku serii (od 1 do 3) w ciągu jednego dnia
        num_series_today = random.randint(1, 3)
        day_hours = sorted([random.randint(7, 21) for _ in range(num_series_today)])

        for series_idx in range(num_series_today):
            # Calculate localized randomized set repetition volume limits
            total_reps = int(base_total_reps + random.choice([-1, 0, 1]))
            total_reps = max(5, total_reps)

            correct_reps = round(total_reps * base_correct_ratio)
            correct_reps = min(total_reps, max(0, correct_reps))
            faulty_reps = total_reps - correct_reps

            duration = total_reps * 3 + random.randint(4, 10)
            repetitions = []

            # Populate ideal form instances
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

            # MODYFIKACJA 2: Poprawa generowania wielu błędów jednocześnie
            for _ in range(faulty_reps):
                # Każdy błąd ma niezależną szansę (np. 50%) na wystąpienie,
                # co pozwala na nakładanie się wielu błędów w jednym powtórzeniu
                legs_bent = random.random() < 0.5
                bad_torso_angle = random.random() < 0.5
                too_wide = random.random() < 0.5
                # Jeśli jest zbyt szeroko, nie może być zbyt wąsko i na odwrót
                too_narrow = False if too_wide else (random.random() < 0.5)

                # Bezpiecznik: jeśli wylosował się brak błędów, wymuszamy przynajmniej dwa
                if not (legs_bent or bad_torso_angle or too_wide or too_narrow):
                    legs_bent = True
                    bad_torso_angle = True

                repetitions.append(
                    {
                        "speed": round(random.uniform(3.2, 4.8), 1),
                        "quality": "Faulty",
                        "errors": {
                            "too_narrow": too_narrow,
                            "too_wide": too_wide,
                            "legs_bent": legs_bent,
                            "bad_torso_angle": bad_torso_angle,
                        },
                    }
                )

            random.shuffle(repetitions)

            # Build final metadata transaction payload map
            hour = day_hours[series_idx]
            minute = random.randint(0, 59)
            exec_datetime = current_date.replace(hour=hour, minute=minute)

            series_payload = {
                "metadata": {
                    "date": exec_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "location": random.choice(["Gym", "Home", "Park"]),
                    "duration_seconds": duration,
                },
                "repetitions": repetitions,
            }

            series_list.append(series_payload)

        # Przejście do kolejnego dnia (trening co 2-4 dni)
        current_date += timedelta(days=random.randint(2, 4))

    # Serialize object output context targeting specified storage profiles
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(series_list, f, indent=2, ensure_ascii=False)

    print(
        f"Generated {len(series_list)} history entries ({profile_type}) into '{output_filename}'"
    )


if __name__ == "__main__":
    # Example execution: profile selector tests
    generate_parameterized_workout_data(
        profile_type="linear_progress", output_filename="linear_progress.json"
    )
    generate_parameterized_workout_data(
        profile_type="fatigue_regression",
        output_filename="fatigue_regression.json",
    )
    generate_parameterized_workout_data(
        profile_type="plateau", output_filename="plateau.json"
    )
