# ==> ./dataStorageModule/test/generate_mock_progress.py <==
import json
import random
from datetime import datetime, timedelta


def generate_parameterized_workout_data(
    profile_type="linear_progress", output_filename="workout_history.json"
):
    """
    Generates tailored tracking profiles to mock real trainer progress variables.

    Supported profile_types:
      - 'linear_progress': Smooth continuous improvements in volume and accuracy.
      - 'fatigue_regression': Initial peaks followed by drop-offs in quality.
      - 'plateau': Rapid early adaptation followed by complete stabilization.
    """
    # Define time boundaries matching project timelines
    end_date = datetime(2026, 6, 13, 18, 0, 0)
    current_date = end_date - timedelta(days=120)

    series_list = []
    workout_index = 0

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
        workout_index += 1

        # Profile tracking adjustment mechanics
        if profile_type == "linear_progress":
            if workout_index % 2 == 0:
                base_total_reps += random.choice([0, 1])
                base_correct_ratio = min(0.96, base_correct_ratio + 0.015)

        elif profile_type == "fatigue_regression":
            if workout_index > 15:
                # Fatigue accumulation begins dropping accuracy margins
                base_total_reps = max(6, base_total_reps - random.choice([0, 0, 1]))
                base_correct_ratio = max(0.40, base_correct_ratio - 0.02)

        elif profile_type == "plateau":
            if workout_index < 12:
                # Early fast tracking adaptation gains
                if workout_index % 2 == 0:
                    base_total_reps += 1
                    base_correct_ratio = min(0.80, base_correct_ratio + 0.04)
            # Beyond index 12, values freeze to simulate a plateau

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

        # Populate multi-flag error configurations simultaneously
        for _ in range(faulty_reps):
            legs_bent = random.choice([True, False])
            bad_torso_angle = random.choice([True, False])

            # Mismatched separation options configuration
            too_wide = random.choice([True, False]) if not legs_bent else False
            too_narrow = False if too_wide else random.choice([True, False])

            # Edge case insurance: ensure at least one error flag is active
            if not (legs_bent or bad_torso_angle or too_wide or too_narrow):
                legs_bent = True

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
        hour = random.randint(7, 21)
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
        profile_type="fatigue_regression", output_filename="fatigue_regression.json"
    )
    generate_parameterized_workout_data(
        profile_type="plateau", output_filename="plateau.json"
    )
