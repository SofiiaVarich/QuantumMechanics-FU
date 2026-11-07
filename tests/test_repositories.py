from datetime import datetime, timedelta, timezone
from pathlib import Path

from quantum_tutor.domain.spaced_repetition import schedule_review
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


def test_curriculum_loads_chapters() -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapters = repository.chapters()
    assert [chapter.number for chapter in chapters] == list(range(1, 21))
    assert chapters[1].formulas[0].id == "c2-born-rule"
    assert chapters[10].title_de == "Schwarzkörperstrahlung"
    assert chapters[10].date == "03.11.2026"
    assert sum(chapter.professor == "Franke" for chapter in chapters) == 10
    ids = [formula.id for chapter in chapters for formula in chapter.formulas]
    assert len(ids) == len(set(ids))


def test_curriculum_does_not_load_obsolete_catalog(tmp_path: Path) -> None:
    (tmp_path / "chapter_01.json").write_text("not an active topic file")
    (tmp_path / "experiments.json").write_text("not an active topic file")
    assert CurriculumRepository(tmp_path).chapters() == []


def test_formula_notation_contains_no_placeholder_stars() -> None:
    repository = CurriculumRepository(Path("curriculum"))
    forbidden = {"★", "⋆", "*"}
    for chapter in repository.chapters():
        for formula in chapter.formulas:
            assert not any(character in formula.equation for character in forbidden), formula.id
            assert not any(
                character in symbol
                for symbol in formula.symbols
                for character in forbidden
            ), formula.id


def test_progress_is_persisted(tmp_path: Path) -> None:
    repository = ProgressRepository(tmp_path / "test.db")
    now = datetime.now(timezone.utc) - timedelta(days=2)
    state = schedule_review(42, "term-1", "term", False, now=now)
    repository.save_answer(state, False)
    assert repository.repetition_count(42, "term-1") == 0
    assert repository.due_item_ids(42, datetime.now(timezone.utc)) == ["term-1"]
    assert repository.statistics(42) == (1, 0)
    assert repository.mastery_counts(42) == (1, 0, 0)
