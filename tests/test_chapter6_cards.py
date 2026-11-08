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


def test_chapter6_import_and_parent_set(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(6)
    assert chapter is not None
    assert len(chapter.concepts) == 85
    assert Counter(card.section_id for card in chapter.concepts) == {
        "6.1": 3, "6.1.1": 30, "6.1.2": 8, "6.1.3": 10,
        "6.2": 7, "6.2.1": 10, "6.2.2": 6, "6.3": 11,
    }
    assert all(card.section_id in {section.id for section in chapter.sections} for card in chapter.concepts)
    ids = [card.id for item in repository.chapters() for card in item.concepts]
    assert len(ids) == len(set(ids))
    first = chapter.concepts[0]
    assert first.id == "C6-001"
    assert first.key_rule == "H⁽⁰⁾ = Σⱼ Eⱼ⁽⁰⁾ |ψⱼ⁽⁰⁾⟩⟨ψⱼ⁽⁰⁾|"
    assert first.definition == "Known eigenvalues and eigenvectors form the starting point."
    metadata = json.loads(Path("curriculum/topic_6.json").read_text())["concept_metadata"]
    assert metadata[first.id]["equation_reference"] == "6.1"
    assert {f"C6-{i:03}" for i in range(1, 48)}.issubset({card.id for card in chapter.concepts})
    assert metadata[first.id]["formula_latex"].startswith(r"H^{(0)}=\sum_j")
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "progress.db")), repository, (123,)
    )[-1]
    message = SimpleNamespace(text="6.1 Time independent perturbation theory · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/51" in message.reply_text.call_args.args[0]
    assert sum(context.user_data["concept_choices"].values()) == 1
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["study_set"].pending[-1].id == first.id
    assert context.user_data["question"].item_id != first.id
    assert any(first.key_rule in call.args[0] for call in message.reply_text.call_args_list)
