from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Repetition:
    id: Optional[int] = None
    execution_speed_seconds: float = 0.0
    quality_status: str = "CORRECT"
    error_too_shallow: bool = False
    error_too_far_from_chair: bool = False
    error_lacks_tempo_control: bool = False


@dataclass
class Set:
    id: Optional[int] = None
    execution_date: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    location: str = "Home"
    duration_seconds: int = 0
    repetitions: List[Repetition] = field(default_factory=list)

    def summarize_set(self):
        total_reps = len(self.repetitions)
        correct_reps = sum(1 for r in self.repetitions if r.quality_status == "CORRECT")
        faulty_reps = total_reps - correct_reps
        return total_reps, correct_reps, faulty_reps
