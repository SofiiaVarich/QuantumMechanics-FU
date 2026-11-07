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


def test_chapter8_import_and_sets(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(8)
    assert chapter is not None
    assert len(chapter.concepts) == 31
    assert Counter(card.section_id for card in chapter.concepts) == {
        "8.1": 6, "8.2.1": 5, "8.2.2": 5, "8.2.3": 5,
        "8.3.1": 3, "8.3.2": 4, "8.3.3": 3,
    }
    assert all(card.section_id in {section.id for section in chapter.sections} for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C8-001"
    assert first.key_rule == "H = (P − eA/c)²/(2m) + eΦ"
    assert first.definition == "Minimal coupling of a spinless charged particle to vector and scalar potentials."
    metadata = json.loads(Path("curriculum/topic_08.json").read_text())["concept_metadata"]
    assert metadata[first.id]["equation_reference"] == "8.1"
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="8.1 Hamilton operator of spinless particles · 0%", reply_text=AsyncMock())
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
    message.text = "8.2 Constant magnetic field · 0%"
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == 15
    message.text = "8.3 Concluding remarks · 0%"
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == 10
