from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quantum_tutor.domain.models import ReviewState


_INTERVALS = (1, 3, 7, 14, 30, 60)


def schedule_review(
    user_id: int,
    item_id: str,
    item_type: str,
    correct: bool,
    previous_repetitions: int = 0,
    now: datetime | None = None,
) -> ReviewState:
    """Schedule a review using a small, deterministic Leitner-style progression."""
    current = now or datetime.now(timezone.utc)
    repetitions = min(previous_repetitions + 1, len(_INTERVALS)) if correct else 0
    interval = _INTERVALS[max(repetitions - 1, 0)]
    return ReviewState(
        user_id=user_id,
        item_id=item_id,
        item_type=item_type,
        interval_days=interval,
        repetitions=repetitions,
        due_at=current + timedelta(days=interval),
    )
