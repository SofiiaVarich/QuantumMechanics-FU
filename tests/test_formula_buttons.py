import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers, HOME, DONT_KNOW


def test_actual_answer_keyboard_shows_equations_in_learn_mode(tmp_path: Path) -> None:
    repository = CurriculumRepository(Path("curriculum"))
    service = StudyService(repository, ProgressRepository(tmp_path / "db"))
    handler = build_handlers(service, repository, (123,))[-1]
    message = SimpleNamespace(text="3️⃣ Quantendynamik · 0%", reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(user_data={})
    asyncio.run(handler(update, context))
    labels = [button.text for row in message.reply_text.call_args.kwargs["reply_markup"].keyboard for button in row]
    equation = repository.chapter(3).concepts[0].definition
    assert any(equation in label for label in labels)
    assert "Which formula" in message.reply_text.call_args.args[0]
    assert HOME in labels and DONT_KNOW in labels
    assert not any("Assumptions:" in label or "\\frac" in label for label in labels)
    # The exact button text grades correctly and advances the set.
    message.text = next(label for label, correct in context.user_data["concept_choices"].items() if correct)
    asyncio.run(handler(update, context))
    assert len(context.user_data["study_set"].mastered) == 1


def test_assumptions_remain_in_feedback_not_formula_button(tmp_path: Path) -> None:
    service = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(tmp_path / "db"))
    card = service.cards(1)[0]
    exercise = service.set_exercise(card)
    correct = exercise.choices[exercise.correct_index]
    assert correct == "λ = h / p"
    assert "Assumptions:" in exercise.question.answer
