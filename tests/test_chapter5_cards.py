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


def test_chapter5_cards_and_automatic_sets(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(5)
    assert chapter is not None
    assert len(chapter.concepts) == 59
    assert Counter(card.section_id for card in chapter.concepts) == {
        "5.1.1": 6, "5.1.2": 3, "5.1.3": 12, "5.1.4": 14,
        "5.2.1": 7, "5.2.2": 10, "5.2.3": 7,
    }
    sections = {section.id for section in chapter.sections}
    assert all(card.section_id in sections for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C5-001"
    assert first.key_rule == "L = X × P"
    assert first.definition == "Angular momentum is the cross product of position and momentum operators."
    metadata = json.loads(Path("curriculum/topic_05.json").read_text())["concept_metadata"]
    assert metadata[first.id]["equation_reference"] == "5.1"
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="5.1.1 Definition · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/6" in message.reply_text.call_args.args[0]
    assert sum(context.user_data["concept_choices"].values()) == 1
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first.id
    assert context.user_data["question"].item_id != first.id
    assert any(first.key_rule in call.args[0] for call in message.reply_text.call_args_list)
