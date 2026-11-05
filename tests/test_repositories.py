from datetime import datetime, timedelta, timezone
from pathlib import Path

from quantum_tutor.domain.spaced_repetition import schedule_review
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


def test_curriculum_loads_chapters() -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapters = repository.chapters()
    assert [chapter.number for chapter in chapters] == list(range(1, 11))
    assert chapters[1].formulas[0].id == "c2-born-rule"


def test_progress_is_persisted(tmp_path: Path) -> None:
    repository = ProgressRepository(tmp_path / "test.db")
    now = datetime.now(timezone.utc) - timedelta(days=2)
    state = schedule_review(42, "term-1", "term", False, now=now)
    repository.save_answer(state, False)
    assert repository.repetition_count(42, "term-1") == 0
    assert repository.due_item_ids(42, datetime.now(timezone.utc)) == ["term-1"]
    assert repository.statistics(42) == (1, 0)
