import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers


def test_original_headings_are_clickable_without_pdf_notice(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "test.db"))
    text_handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="1️⃣ Einführung in die Quantenmechanik", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(text_handler(update, context))
    calls = message.reply_text.call_args_list
    content = "\n".join(call.args[0] for call in calls)
    assert ".pdf" not in content
    assert "Übersetzungen" not in content
    assert "1.1 What is quantum mechanics?" in content
    keyboard = calls[-1].kwargs["reply_markup"]
    labels = [button.text for row in keyboard.keyboard for button in row]
    assert "1.1.1 Boxes and Stern-Gerlach devices · — no cards" in labels
    message.text = "1.1.1 Boxes and Stern-Gerlach devices"
    asyncio.run(text_handler(update, context))
    assert context.user_data["selected_section"] == "1.1.1"
    assert "Section-specific lessons are not available yet" in message.reply_text.call_args.args[0]
