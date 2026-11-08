import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.domain.spaced_repetition import schedule_review
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, REVIEW


def test_review_includes_missed_and_due_cards_from_all_topics(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    path = tmp_path / "reviews.db"
    progress = ProgressRepository(path)
    missed = repository.chapter(4).concepts[0]
    formula = repository.chapter(1).formulas[0]
    progress.save_answer(schedule_review(123, missed.id, "concept", False), False)
    progress.save_answer(schedule_review(
        123, formula.id, "formula", True,
        now=datetime.now(timezone.utc) - timedelta(days=2),
    ), True)
    progress.save_answer(schedule_review(456, "other-user", "concept", False), False)
    service = StudyService(repository, ProgressRepository(path))
    assert {card.id for card in service.review_cards(123)} == {missed.id, formula.id}
    assert service.review_cards(456) == ()  # Stale/unknown IDs cannot produce playable cards.
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text=REVIEW, reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={"selected_chapter": 2})
    asyncio.run(handler(update, context))
    assert context.user_data["set_kind"] == "review"
    assert {card.id for card in context.user_data["study_set"].cards} == {missed.id, formula.id}
    assert "selected_chapter" not in context.user_data
    assert "1/2" in message.reply_text.call_args.args[0]
    # Completing the review leaves both items scheduled for the future.
    for _ in range(2):
        message.text = next(label for label, correct in context.user_data["concept_choices"].items() if correct)
        asyncio.run(handler(update, context))
    assert "study_set" not in context.user_data
    assert service.review_cards(123) == ()
