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


def test_chapter9_import_and_sets(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(9)
    assert chapter is not None
    assert len(chapter.concepts) == 33
    assert Counter(card.section_id for card in chapter.concepts) == {
        "9.1": 2, "9.2": 4, "9.3.1": 4, "9.3.2": 5,
        "9.3.3": 5, "9.4": 11, "9.5": 2,
    }
    assert all(card.section_id in {section.id for section in chapter.sections} for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C9-001"
    assert first.front == "Absolute randomness"
    assert first.key_rule == "Quantum measurement outcomes are presented as intrinsically random."
    assert first.definition == "The chapter asks whether underlying local hidden variables could explain outcomes."
    metadata = json.loads(Path("curriculum/topic_9.json").read_text())["concept_metadata"]
    assert metadata[first.id]["source_reference"] == "QMChapter9(1).pdf"
    assert metadata[first.id]["equation_reference"] == "—"
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="9.1 Introduction · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/2" in message.reply_text.call_args.args[0]
    assert sum(context.user_data["concept_choices"].values()) == 1
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first.id
    assert context.user_data["question"].item_id != first.id
    assert any(first.key_rule in call.args[0] for call in message.reply_text.call_args_list)
    message.text = "9.3 Preliminaries · 0%"
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == 14
