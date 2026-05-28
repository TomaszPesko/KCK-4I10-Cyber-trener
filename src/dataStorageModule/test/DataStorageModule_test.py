import time
from unittest.mock import Mock

import pytest

from src.dataStorageModule.DataStorageModule import *
from src.include.set_data import *


@pytest.fixture
def db_service():
    """
    Fixture creating an instance of the database module in RAM (:memory:).
    Starts the thread before the test and ensures it closes properly after the test.
    """
    service = DataStorageModule(db_path=":memory:")
    service.start()

    yield service

    service.task_queue.put(None)
    service.join(timeout=2)


def test_summarize_set_calculates_correct_stats():
    """Unit test for the internal logic of the Set class (no database involved)."""
    workout_set = Set()
    workout_set.repetitions.append(Repetition(quality_status="CORRECT"))
    workout_set.repetitions.append(
        Repetition(quality_status="ERROR", error_too_shallow=True)
    )
    workout_set.repetitions.append(Repetition(quality_status="CORRECT"))

    total, correct, faulty = workout_set.summarize_set()

    assert total == 3
    assert correct == 2
    assert faulty == 1


def test_save_and_get_statistics(db_service):
    """Integration test: saving a set to the DB and verifying general statistics."""
    workout_set = Set(location="Home", duration_seconds=15)
    workout_set.repetitions.append(
        Repetition(execution_speed_seconds=2.0, quality_status="CORRECT")
    )
    workout_set.repetitions.append(
        Repetition(
            execution_speed_seconds=2.5, quality_status="ERROR", error_too_shallow=True
        )
    )

    callback_mock = Mock()

    db_service.request_set_save(workout_set)

    db_service.task_queue.join()

    db_service.request_statistics(callback_mock)

    db_service.task_queue.join()

    callback_mock.assert_called_once()

    stats_result = callback_mock.call_args[0][0]

    assert stats_result == (1, 2, 1)


def test_multiple_sets_saving(db_service):
    """Test checks if adding subsequent sets correctly aggregates statistics."""
    s1 = Set()
    s1.repetitions.append(Repetition(quality_status="CORRECT"))

    s2 = Set()
    s2.repetitions.append(Repetition(quality_status="CORRECT"))
    s2.repetitions.append(
        Repetition(quality_status="ERROR", error_too_far_from_chair=True)
    )

    callback_mock = Mock()

    db_service.request_set_save(s1)
    db_service.request_set_save(s2)
    db_service.task_queue.join()

    db_service.request_statistics(callback_mock)
    db_service.task_queue.join()

    result = callback_mock.call_args[0][0]
    # Expected: 2 sets, 3 total repetitions, 2 total correct repetitions
    assert result == (2, 3, 2)
