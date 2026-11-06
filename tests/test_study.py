from pathlib import Path

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


def test_adaptive_exercise_contains_one_correct_choice(tmp_path: Path) -> None:
    service = StudyService(
        CurriculumRepository(Path("curriculum")),
        ProgressRepository(tmp_path / "progress.db"),
    )
    exercise = service.adaptive_exercise("formula")
    assert exercise is not None
    assert exercise.question.item_type == "formula"
    assert 3 <= len(exercise.choices) <= 4
    assert exercise.choices[exercise.correct_index] in exercise.question.answer
    assert service.item_count("term") == 0
    assert service.item_count("formula") == 12
    assert service.item_count("all") == 12
    assert service.item_count("law") == 12

    law = service.random_law()
    assert law is not None
    assert "APPLICATION" in law.prompt
    assert "LAW / FORMULA" in law.answer

    chapter_three = service.adaptive_exercise("formula", chapter_number=3)
    assert chapter_three is not None
    assert chapter_three.question.item_id == "c3-schrodinger"
    assert service.item_count("formula", chapter_number=3) == 1
    assert service.adaptive_exercise(chapter_number=5) is None
