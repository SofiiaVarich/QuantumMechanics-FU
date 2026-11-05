from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from quantum_tutor.domain.models import Formula, Term
from quantum_tutor.domain.spaced_repetition import schedule_review
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


@dataclass(frozen=True)
class Question:
    item_id: str
    item_type: str
    prompt: str
    answer: str


class StudyService:
    def __init__(self, curriculum: CurriculumRepository, progress: ProgressRepository) -> None:
        self.curriculum = curriculum
        self.progress = progress

    def random_term(self) -> Question | None:
        terms = [term for chapter in self.curriculum.chapters() for term in chapter.terms]
        if not terms:
            return None
        term = random.choice(terms)
        return Question(term.id, "term", f"Translate and explain: {term.german}",
                        f"{term.english} — {term.definition}")

    def random_formula(self) -> Question | None:
        formulas = [formula for chapter in self.curriculum.chapters() for formula in chapter.formulas]
        if not formulas:
            return None
        formula = random.choice(formulas)
        return Question(formula.id, "formula", f"Recall the equation: {formula.name_de}",
                        f"{formula.name}: {formula.equation}\nUse: {formula.when_to_use}")

    def record(self, user_id: int, question: Question, correct: bool) -> None:
        previous = self.progress.repetition_count(user_id, question.item_id)
        state = schedule_review(user_id, question.item_id, question.item_type, correct, previous)
        self.progress.save_answer(state, correct)

    def due_count(self, user_id: int) -> int:
        return len(self.progress.due_item_ids(user_id, datetime.now(timezone.utc)))

    def progress_text(self, user_id: int) -> str:
        total, correct = self.progress.statistics(user_id)
        accuracy = round(correct / total * 100) if total else 0
        return f"Answered: {total}\nCorrect: {correct}\nAccuracy: {accuracy}%\nDue reviews: {self.due_count(user_id)}"
