import asyncio
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, DONT_KNOW


def test_chapter10_import_and_sets(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(10)
    assert chapter is not None
    assert len(chapter.concepts) == 71
    assert Counter(card.section_id for card in chapter.concepts) == {
        "10.1.1": 8, "10.1.2": 10, "10.1.3": 8, "10.1.4": 9,
        "10.2.1": 3, "10.2.2": 1, "10.3.1": 4, "10.3.2": 9,
        "10.3.3": 16, "10.4.1": 2, "10.4.2": 1,
    }
    assert all(card.section_id in {section.id for section in chapter.sections} for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C10-001"
    assert first.key_rule == "System S interacts with environment E"
    assert first.definition == "The subsystem is described by its reduced density operator."
    metadata = json.loads(Path("curriculum/topic_10.json").read_text())["concept_metadata"]
    assert metadata[first.id]["equation_reference"] == "p. 3"
    assert metadata[first.id]["priority"] == "Medium"
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="10.1 Open quantum systems · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == 35
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first.id
    assert context.user_data["question"].item_id != first.id
    message.text = "10.4.2 Quantum computing · 0%"
    asyncio.run(handler(update, context))
    assert "1/1" in message.reply_text.call_args.args[0]
    assert len(context.user_data["concept_choices"]) == 4
    card_id = context.user_data["question"].item_id
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["question"].item_id == card_id
    message.text = next(label for label, correct in context.user_data["concept_choices"].items() if correct)
    asyncio.run(handler(update, context))
    assert "study_set" not in context.user_data
    assert any("100% completed in this set" in call.args[0] for call in message.reply_text.call_args_list)
