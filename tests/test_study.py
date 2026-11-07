from pathlib import Path

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


def test_active_catalog_combines_concepts_and_formulas(tmp_path: Path) -> None:
    curriculum = CurriculumRepository(Path("curriculum"))
    service = StudyService(curriculum, ProgressRepository(tmp_path / "progress.db"))
    cards = service.cards()
    expected = {
        item.id
        for chapter in curriculum.chapters()
        for item in (*chapter.concepts, *chapter.formulas)
    }
    assert {card.id for card in cards} == expected
    assert len(cards) == len(expected)
    assert len(cards) == 555
    assert {card.id for card in service.cards(3)} == {
        item.id for item in (*curriculum.chapter(3).concepts, *curriculum.chapter(3).formulas)
    }
    assert service.cards(999) == ()
