from datetime import time

import pytest

from quantum_tutor.scheduler import parse_reminder_times


def test_parse_reminder_times() -> None:
    assert parse_reminder_times("05:30, 20:00") == (time(5, 30), time(20, 0))


def test_invalid_reminder_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="expected HH:MM"):
        parse_reminder_times("tomorrow")
