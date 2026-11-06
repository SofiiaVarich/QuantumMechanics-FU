from pathlib import Path

from quantum_tutor.domain.spaced_repetition import schedule_review
from quantum_tutor.infrastructure.database import ProgressRepository


def test_known_progress_persists_is_private_and_can_decrease(tmp_path: Path) -> None:
    path = tmp_path / "progress.db"
    repository = ProgressRepository(path)
    repository.save_answer(schedule_review(1, "card", "concept", True), True)
    assert ProgressRepository(path).known_item_ids(1) == {"card"}
    assert repository.known_item_ids(2) == set()
    repository.save_answer(schedule_review(1, "card", "concept", False), False)
    assert repository.known_item_ids(1) == set()
