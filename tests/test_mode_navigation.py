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
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
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
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    labels = [b.text for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard for b in row]
    assert len([label for label in labels if label.startswith("📖 ")]) == 10
    assert len([label for label in labels if label.startswith("🔬 E")]) == 10
    assert "📖 2️⃣ · Zustände & Observablen · 0%" in labels
    assert "📖 🔟 · Atome, Moleküle & Quantencomputer · 0%" in labels
    assert "E1 · Schwarzkörperstrahlung · 03.11.2026" in message.reply_text.call_args.args[0]
    assert "E10 · Spin-Bahn-Kopplung · Termin offen" in message.reply_text.call_args.args[0]
    experiment = "🔬 E1 · Schwarzkörperstrahlung · 0%"
    assert experiment in labels
    message.text = experiment
    asyncio.run(handler(update, context))
    assert context.user_data["selected_chapter"] == 11
    assert len(context.user_data["study_set"].cards) == 12
    # A menu already sent under the old name still opens the new selector.
    message.text = "🗂 Topics"
    asyncio.run(handler(update, context))
    assert "Choose a chapter or experiment" in message.reply_text.call_args.args[0]


@pytest.mark.parametrize("percentage", [None, "0%", "87%", "100%", "— no cards"])
def test_all_topic_keyboard_generations_route_stably(tmp_path: Path, percentage) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "db"))
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text=TOPICS, reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message, effective_user=SimpleNamespace(id=123),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    labels = [row[0].text.rsplit(" · ", 1)[0]
              for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard[:-1]]
    digits = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
    for chapter, short_label in zip(repository.chapters(), labels, strict=True):
        if chapter.professor == "Eisert":
            number = digits[chapter.number - 1]
            old_labels = [f"{number} {chapter.title_de}", f"📖 Chapter {number} · {chapter.title_de}"]
        else:
            date = chapter.date or "Termin offen"
            old_labels = [f"🔬 {date} · {chapter.title_de}", f"🔬 Experiment · {chapter.title_de} · {date}"]
        for label in [short_label, *old_labels]:
            message.text = label if percentage is None else f"{label} · {percentage}"
            context.user_data.clear()
            message.reply_text.reset_mock()
            asyncio.run(handler(update, context))
            assert context.user_data["selected_chapter"] == chapter.number
            assert tuple(card.id for card in context.user_data["study_set"].cards) == tuple(
                card.id for card in service.mode_cards(chapter.number, "learn")
            )
            assert message.reply_text.call_args_list[0].args[0] == f"📖 {chapter.title_de} · {len(service.mode_cards(chapter.number, 'learn'))} cards"


@pytest.mark.parametrize("old,new", [
    ("⚖️ Laws & Rules", "⚖️ Laws"),
    ("🗂 Chapters & Experiments", "🗂 Topics"),
    ("🏠 Main menu", "🏠 Menu"),
    ("📱 Open Mini App", "📱 App"),
    ("🌐 Open Mini App", "📱 App"),
    ("Open Mini App", "📱 App"),
    ("🎯 Learn", "🎯 Learn"),
    ("🧮 Formulas", "🧮 Formulas"),
    ("🔁 Review", "🔁 Review"),
    ("📈 Progress", "📈 Progress"),
])
def test_old_controls_match_new_controls(tmp_path: Path, old, new) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    handler = build_handlers(
        StudyService(repository, ProgressRepository(tmp_path / "db")), repository, (123,),
        mini_app_url="https://example.com/app",
    )[-1]
    results = []
    for text in (old, new):
        message = SimpleNamespace(text=text, reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=123),
            effective_chat=SimpleNamespace(id=123, type="private"),
        )
        context = SimpleNamespace(user_data={"mode": "concept_choice", "question": object()})
        asyncio.run(handler(update, context))
        results.append(([call for call in message.reply_text.call_args_list], context.user_data.get("requested_mode")))
        assert "did not recognize" not in message.reply_text.call_args.args[0]
    assert results[0] == results[1]


def test_main_labels_are_concise() -> None:
    from quantum_tutor.presentation.handlers import main_keyboard

    assert [button.text for row in main_keyboard("https://example.com").keyboard for button in row] == [
        "📱 App", "🎯 Learn", "⚖️ Laws", "🧮 Formulas", "🗂 Topics", "🔁 Review", "📈 Progress",
    ]
    assert HOME == "🏠 Menu"
    assert DONT_KNOW == "🔁 Don't know"


def test_unauthorized_new_mode_cannot_start_session(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    handler = build_handlers(StudyService(repository, ProgressRepository(tmp_path / "db")), repository, (123,))[-1]
    message = SimpleNamespace(text=FORMULAS, reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=456),
        effective_chat=SimpleNamespace(id=456, type="private"),
    )
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    assert context.user_data == {}
    assert "private" in message.reply_text.call_args.args[0]
