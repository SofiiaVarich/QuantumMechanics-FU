import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, DONT_KNOW, REVIEW


def test_all_experimental_cards_and_source_metadata() -> None:
    repository = CurriculumRepository(Path("curriculum"))
    expected = {11: 10, 12: 5, 13: 4, 14: 4, 15: 5, 16: 7, 17: 3, 18: 3, 19: 2, 20: 5}
    all_ids = [card.id for chapter in repository.chapters() for card in chapter.concepts]
    assert len(all_ids) == len(set(all_ids))
    imported = []
    for number, count in expected.items():
        chapter = repository.chapter(number)
        assert chapter is not None
        assert len(chapter.concepts) == count
        metadata = json.loads(Path(f"curriculum/topic_{number:02}.json").read_text())["concept_metadata"]
        for card in chapter.concepts:
            assert card.section_id == str(number)
            assert "\\" not in card.key_rule
            assert "not verified against Franke slides" in metadata[card.id]["source_status"]
            assert "original_formula" in metadata[card.id]
            imported.append(card.id)
    assert set(imported) == {f"EXP-{number:03}" for number in range(1, 49)}
    assert repository.chapter(11).date == "03.11.2026"
    assert repository.chapter(13).date == repository.chapter(14).date == "10.11.2026"
    assert repository.chapter(20).date is None
    data = json.loads(Path("curriculum/topic_11.json").read_text())
    assert data["concept_metadata"]["EXP-002"]["original_formula"] == r"E_n=(n+\tfrac12)hν"
    assert next(card for card in repository.chapter(11).concepts if card.id == "EXP-002").key_rule == "Eₙ = (n + ½)hν"


def test_experimental_topic_set_and_review(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "progress.db"))
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="🔬 03.11.2026 · Schwarzkörperstrahlung · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == len(service.cards(11)) == 12
    first = context.user_data["question"].item_id
    assert first == "EXP-001"
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first
    message.text = REVIEW
    asyncio.run(handler(update, context))
    assert context.user_data["set_kind"] == "review"
    assert {card.id for card in context.user_data["study_set"].cards} == {first}
