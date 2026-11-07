import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import (
    build_handlers, LEARN, FORMULAS, LAWS, TOPICS, HOME, REVIEW, DONT_KNOW,
)


@pytest.mark.parametrize("button,mode,index", [(LEARN, "learn", 2), (FORMULAS, "formula", 4), (LAWS, "law", 3)])
def test_buttons_and_commands_choose_topic_then_start_correct_set(tmp_path: Path, button, mode, index) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "db.sqlite"))
    handlers = build_handlers(service, repository, (123,))
    message = SimpleNamespace(text=button, reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={"selected_chapter": 1, "mode": "old"})
    asyncio.run(handlers[-1](update, context))
    assert context.user_data["requested_mode"] == mode
    assert "selected_chapter" not in context.user_data
    assert "Choose a chapter or experiment" in message.reply_text.call_args.args[0]
    message.text = "5️⃣ Drehimpuls und rotationsinvariante Probleme · 0%"
    asyncio.run(handlers[-1](update, context))
    session = context.user_data["study_set"]
    assert tuple(card.id for card in session.cards) == tuple(card.id for card in service.mode_cards(5, mode))
    assert len(session.cards) > 0  # Previously this chapter's formulas mode was empty.
    assert context.user_data["session_mode"] == mode
    if mode == "formula":
        assert all(service.has_formula(card) for card in session.cards)
        assert "Which formula" in message.reply_text.call_args.args[0]
    labels = [b.text for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard for b in row]
    assert HOME in labels and DONT_KNOW in labels
    assert not any(label in labels for label in (LEARN, FORMULAS, LAWS, TOPICS, REVIEW))
    # Slash commands select modes through the same topic picker.
    asyncio.run(handlers[index](update, context))
    assert "study_set" not in context.user_data
    assert context.user_data["requested_mode"] == mode


def test_chapters_and_experiments_labels_are_clear_and_selectable(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    handler = build_handlers(StudyService(repository, ProgressRepository(tmp_path / "db")), repository, (123,))[-1]
    message = SimpleNamespace(text=TOPICS, reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    labels = [b.text for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard for b in row]
    assert len([label for label in labels if label.startswith("📖 Chapter ")]) == 10
    assert len([label for label in labels if label.startswith("🔬 Experiment · ")]) == 10
    assert "📖 Chapter 2️⃣ · Quantenzustände und Observablen · 0%" in labels
    experiment = "🔬 Experiment · Schwarzkörperstrahlung · 03.11.2026 · 0%"
    assert experiment in labels
    message.text = experiment
    asyncio.run(handler(update, context))
    assert context.user_data["selected_chapter"] == 11
    assert len(context.user_data["study_set"].cards) == 12
    # A menu already sent under the old name still opens the new selector.
    message.text = "🗂 Topics"
    asyncio.run(handler(update, context))
    assert "Choose a chapter or experiment" in message.reply_text.call_args.args[0]


def test_unauthorized_new_mode_cannot_start_session(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    handler = build_handlers(StudyService(repository, ProgressRepository(tmp_path / "db")), repository, (123,))[-1]
    message = SimpleNamespace(text=FORMULAS, reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=456))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert context.user_data == {}
    assert "private" in message.reply_text.call_args.args[0]
