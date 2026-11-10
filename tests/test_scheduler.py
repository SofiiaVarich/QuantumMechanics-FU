from datetime import date, time

import pytest

from quantum_tutor.scheduler import exam_countdown, parse_reminder_times


def test_exam_countdown() -> None:
    today = date(2027, 2, 1)
    assert exam_countdown(None, today) == ""
    assert exam_countdown(date(2027, 1, 31), today) == ""
    assert "Exam today" in exam_countdown(today, today)
    assert "1 day until" in exam_countdown(date(2027, 2, 2), today)
    assert "2 days until" in exam_countdown(date(2027, 2, 3), today)


def test_parse_reminder_times() -> None:
    assert parse_reminder_times("05:30, 20:00") == (time(5, 30), time(20, 0))


def test_invalid_reminder_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="expected HH:MM"):
        parse_reminder_times("tomorrow")
