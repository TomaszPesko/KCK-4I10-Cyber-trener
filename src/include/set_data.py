from datetime import datetime


class Repetition:

    def __init__(self, speed, quality, shallow=False, far=False, tempo=False):

        self.execution_speed_seconds = float(speed)

        self.quality_status = quality  # "Correct" lub "Faulty"

        self.error_too_shallow = bool(shallow)

        self.error_too_far_from_chair = bool(far)

        self.error_lacks_tempo_control = bool(tempo)


class WorkoutSet:

    def __init__(self, date=None, location="Dom", duration=0):

        self.execution_date = (
            date if date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        self.location = location

        self.duration_seconds = int(duration)

        self.repetitions = []

    def add_repetition(self, rep: Repetition):

        self.repetitions.append(rep)

    def summarize_set(self):

        total = len(self.repetitions)

        correct = sum(1 for r in self.repetitions if r.quality_status == "Correct")

        faulty = total - correct

        return total, correct, faulty
