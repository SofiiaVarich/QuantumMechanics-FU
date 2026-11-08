import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, DONT_KNOW


def test_concept_set_answers_retries_and_completion(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    chapter = repository.chapter(2)
    assert chapter is not None
    assert len(chapter.concepts) == 34
    assert len({card.id for card in chapter.concepts}) == 34
    service = StudyService(repository, ProgressRepository(tmp_path / "progress.db"))
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="2.1.1 State vectors of spin degrees of freedom", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert "1/4 · 0%" in message.reply_text.call_args.args[0]
    labels = [b.text for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard for b in row]
    assert DONT_KNOW in labels
    assert not any(label in labels for label in ("🟠 Hard", "🟢 Easy", "🔵 Okay"))
    first_id = context.user_data["question"].item_id
    message.text = DONT_KNOW
    asyncio.run(handler(update, context))
    assert context.user_data["question"].item_id != first_id
    assert "1/4 · 0%" in message.reply_text.call_args.args[0]
    for _ in range(3):
        message.text = next(label for label, correct in context.user_data["concept_choices"].items() if correct)
        asyncio.run(handler(update, context))
    assert context.user_data["question"].item_id == first_id
    assert "4/4 · 75%" in message.reply_text.call_args.args[0]
    wrong = next(label for label, correct in context.user_data["concept_choices"].items() if not correct)
    message.text = wrong
    asyncio.run(handler(update, context))
    assert context.user_data["question"].item_id == first_id
    message.text = next(label for label, correct in context.user_data["concept_choices"].items() if correct)
    asyncio.run(handler(update, context))
    assert "study_set" not in context.user_data
    calls = message.reply_text.call_args_list
    assert any("100% completed in this set" in call.args[0] for call in calls)
    labels = [button.text for row in calls[-1].kwargs["reply_markup"].keyboard for button in row]
    assert labels == ["🏠 Main menu"]
