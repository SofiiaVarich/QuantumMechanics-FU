from datetime import datetime, timedelta, timezone

from quantum_tutor.domain.spaced_repetition import schedule_review


def test_correct_answer_advances_interval() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = schedule_review(1, "born", "formula", True, previous_repetitions=1, now=now)
    assert state.repetitions == 2
    assert state.interval_days == 3
    assert state.due_at.day == 4


def test_repeat_returns_in_ten_minutes() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = schedule_review(1, "born", "formula", False, previous_repetitions=4, now=now)
    assert state.repetitions == 0
    assert state.interval_days == 0
    assert state.due_at == now + timedelta(minutes=10)


def test_hard_holds_stage_and_easy_skips_a_stage() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    hard = schedule_review(1, "born", "formula", True, 2, now, rating="hard")
    easy = schedule_review(1, "born", "formula", True, 2, now, rating="easy")
    assert hard.repetitions == 2
    assert hard.interval_days == 1
    assert easy.repetitions == 4
    assert easy.interval_days == 14
