import asyncio
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, DONT_KNOW


def test_chapter4_import_and_retry(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(4)
    assert chapter is not None
    assert len(chapter.concepts) == 50
    assert Counter(card.section_id for card in chapter.concepts) == {
        "4.1": 3, "4.2.1": 7, "4.2.2": 6, "4.2.3": 6,
        "4.2.4": 5, "4.2.5": 3, "4.3": 3, "4.4": 4,
        "4.5.1": 3, "4.5.2": 5, "4.5.3": 5,
    }
    sections = {section.id for section in chapter.sections}
    assert all(card.section_id in sections for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    assert chapter.concepts[0].id == "C4-001"
    service = StudyService(repository, ProgressRepository(tmp_path / "progress.db"))
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="4.1 Motivation · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/3" in message.reply_text.call_args.args[0]
    first_id = context.user_data["question"].item_id
    assert sum(context.user_data["concept_choices"].values()) == 1
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["question"].item_id != first_id
    assert context.user_data["study_set"].pending[-1].id == first_id
