from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from quantum_tutor.domain.models import ReviewState

ReviewRating = Literal["repeat", "hard", "okay", "easy"]
_INTERVALS = (1, 3, 7, 14, 30, 60)


def schedule_review(
    user_id: int,
    item_id: str,
    item_type: str,
    correct: bool,
    previous_repetitions: int = 0,
    now: datetime | None = None,
    rating: ReviewRating | None = None,
) -> ReviewState:
    """Schedule a deterministic review while preserving the legacy API.

    Repeat returns in ten minutes, Hard holds the current stage for one day,
    Okay advances one stage, and Easy advances two stages. Binary callers map
    correct to Okay and incorrect to Repeat.
    """
    current = now or datetime.now(timezone.utc)
    selected: ReviewRating = rating or ("okay" if correct else "repeat")

    if selected == "repeat":
        repetitions = 0
        interval_days = 0
        due_at = current + timedelta(minutes=10)
    elif selected == "hard":
        repetitions = max(previous_repetitions, 0)
        interval_days = 1
        due_at = current + timedelta(days=interval_days)
    else:
        step = 2 if selected == "easy" else 1
        repetitions = min(previous_repetitions + step, len(_INTERVALS))
        interval_days = _INTERVALS[max(repetitions - 1, 0)]
        due_at = current + timedelta(days=interval_days)

    return ReviewState(
        user_id=user_id,
        item_id=item_id,
        item_type=item_type,
        interval_days=interval_days,
        repetitions=repetitions,
        due_at=due_at,
    )
