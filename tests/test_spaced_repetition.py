from datetime import datetime, timezone

from quantum_tutor.domain.spaced_repetition import schedule_review


def test_correct_answer_advances_interval() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = schedule_review(1, "born", "formula", True, previous_repetitions=1, now=now)
    assert state.repetitions == 2
    assert state.interval_days == 3
    assert state.due_at.day == 4


def test_incorrect_answer_resets_progress() -> None:
    state = schedule_review(1, "born", "formula", False, previous_repetitions=4)
    assert state.repetitions == 0
    assert state.interval_days == 1
