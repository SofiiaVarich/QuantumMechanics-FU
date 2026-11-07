import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers


def test_topic_starts_all_cards_without_subsection_selection(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "test.db"))
    text_handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="2️⃣ Quantenzustände und Observablen · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(text_handler(update, context))
    session = context.user_data["study_set"]
    chapter = repository.chapter(2)
    assert chapter is not None
    expected = {card.id for card in chapter.concepts} | {formula.id for formula in chapter.formulas}
    assert {card.id for card in session.cards} == expected
    assert len(session.cards) == 31
    content = "\n".join(call.args[0] for call in message.reply_text.call_args_list)
    assert ".pdf" not in content
    assert "Übersetzungen" not in content
    assert "Contents" not in content
    assert "1/31" in content
