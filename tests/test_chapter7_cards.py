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


def test_chapter7_import_and_sets(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(7)
    assert chapter is not None
    assert len(chapter.concepts) == 47
    assert Counter(card.section_id for card in chapter.concepts) == {
        "7.1.1": 6, "7.1.2": 8, "7.1.3": 11,
        "7.2.1": 10, "7.2.2": 2, "7.2.3": 7, "7.2.4": 3,
    }
    sections = {section.id for section in chapter.sections}
    assert all(card.section_id in sections for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C7-001"
    assert first.key_rule == "H = L²(ℝ) ⊗ ℂ²"
    assert first.definition == "Tensor-product structure shown in the script."
    metadata = json.loads(Path("curriculum/topic_7.json").read_text())["concept_metadata"]
    assert metadata[first.id]["equation_reference"] == "7.1"
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="7.1.1 Spin operators · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/6" in message.reply_text.call_args.args[0]
    assert sum(context.user_data["concept_choices"].values()) == 1
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first.id
    assert context.user_data["question"].item_id != first.id
    assert any(first.key_rule in call.args[0] for call in message.reply_text.call_args_list)
    message.text = "7.1 Spin and the problem of adding angular momenta · 0%"
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].cards) == 25
