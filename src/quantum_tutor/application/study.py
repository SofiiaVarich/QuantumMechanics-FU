from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone

from quantum_tutor.domain.models import Formula
from quantum_tutor.domain.spaced_repetition import ReviewRating, schedule_review
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository


@dataclass(frozen=True)
class Question:
    item_id: str
    item_type: str
    prompt: str
    answer: str


@dataclass(frozen=True)
class Exercise:
    question: Question
    choices: tuple[str, ...]
    correct_index: int


class StudyService:
    def __init__(self, curriculum: CurriculumRepository, progress: ProgressRepository) -> None:
        self.curriculum = curriculum
        self.progress = progress

    def _chapters(self, chapter_number: int | None = None):
        chapters = self.curriculum.chapters()
        if chapter_number is None:
            return chapters
        return [chapter for chapter in chapters if chapter.number == chapter_number]


    def random_law(self, chapter_number: int | None = None) -> Question | None:
        formulas = [formula for chapter in self._chapters(chapter_number) for formula in chapter.formulas]
        if not formulas:
            return None
        formula = random.choice(formulas)
        symbols = "; ".join(f"{symbol} = {meaning}" for symbol, meaning in formula.symbols.items())
        answer = self._formula_card(
            formula,
            symbols,
            "; ".join(formula.assumptions) or "None listed",
        )
        return Question(
            formula.id,
            "formula",
            "\n".join((
                "⚖️ Which physical rule is this?",
                "",
                "💡 APPLICATION",
                self._wrap(formula.when_to_use),
            )),
            answer,
        )

    def random_formula(self, chapter_number: int | None = None) -> Question | None:
        formulas = [formula for chapter in self._chapters(chapter_number) for formula in chapter.formulas]
        if not formulas:
            return None
        formula = random.choice(formulas)
        symbols = "; ".join(f"{symbol} = {meaning}" for symbol, meaning in formula.symbols.items())
        assumptions = "; ".join(formula.assumptions) or "None listed"
        table = self._formula_card(formula, symbols, assumptions)
        return Question(formula.id, "formula", f"Recall the equation: {formula.name_de}", table)

    def item_count(self, item_type: str, chapter_number: int | None = None) -> int:
        chapters = self._chapters(chapter_number)
        if item_type in {"formula", "law", "all"}:
            return sum(len(chapter.formulas) for chapter in chapters)
        return 0

    def adaptive_exercise(
        self,
        item_type: str | None = None,
        chapter_number: int | None = None,
    ) -> Exercise | None:
        """Build a recognition exercise with plausible distractors from one category."""
        formulas = [formula for chapter in self._chapters(chapter_number) for formula in chapter.formulas]
        all_formulas = [formula for chapter in self.curriculum.chapters() for formula in chapter.formulas]
        pools: list[tuple[str, list[Formula]]] = []
        if formulas and len(all_formulas) >= 3:
            pools.append(("formula", formulas))
        if item_type is not None:
            pools = [entry for entry in pools if entry[0] == item_type]
        if not pools:
            return None

        _, pool = random.choice(pools)
        selected = random.choice(pool)
        ask_for_law = random.choice((True, False))
        answer = self._compact_formula_card(selected)
        if ask_for_law:
            situation = self._wrap(selected.when_to_use, width=44)
            question = Question(
                selected.id,
                "formula",
                f"🧠 {situation}\n\n❓ Which law or relation applies?",
                answer,
            )
            correct_choice = selected.name
            distractor_pool = [item.name for item in all_formulas if item.id != selected.id]
        else:
            question = Question(
                selected.id,
                "formula",
                f"🧠 {selected.name_de}\n\n❓ Which equation represents this law?",
                answer,
            )
            correct_choice = selected.equation
            distractor_pool = [item.equation for item in all_formulas if item.id != selected.id]

        choices = random.sample(distractor_pool, k=min(3, len(distractor_pool))) + [correct_choice]
        random.shuffle(choices)
        return Exercise(question, tuple(choices), choices.index(correct_choice))

    @staticmethod
    def _wrap(value: str, width: int = 46) -> str:
        return textwrap.fill(value, width=width, break_long_words=False)

    def _compact_formula_card(self, formula: Formula) -> str:
        assumptions = "; ".join(formula.assumptions) or "None listed"
        return "\n".join((
            f"🟢 {formula.name}",
            formula.name_de,
            "",
            f"Formula: {formula.equation}",
            f"Use: {self._wrap(formula.when_to_use, width=42)}",
            "",
            f"🔴 Assumptions: {self._wrap(assumptions, width=42)}",
        ))

    def _formula_card(self, formula: Formula, symbols: str, assumptions: str) -> str:
        return "\n".join((
            "🟢 LAW / FORMULA",
            self._wrap(formula.name),
            self._wrap(formula.name_de),
            "",
            "Formula",
            self._wrap(formula.equation),
            "",
            "Symbols",
            self._wrap(symbols),
            "",
            "Use",
            self._wrap(formula.when_to_use),
            "",
            "🔴 ASSUMPTIONS",
            self._wrap(assumptions),
        ))

    def record(
        self,
        user_id: int,
        question: Question,
        correct: bool,
        rating: ReviewRating | None = None,
        response_ms: int | None = None,
    ) -> None:
        previous = self.progress.repetition_count(user_id, question.item_id)
        state = schedule_review(
            user_id,
            question.item_id,
            question.item_type,
            correct,
            previous,
            rating=rating,
        )
        self.progress.save_answer(state, correct, rating, response_ms)

    def due_count(self, user_id: int) -> int:
        return len(self.progress.due_item_ids(user_id, datetime.now(timezone.utc)))

    def progress_text(self, user_id: int) -> str:
        total, correct = self.progress.statistics(user_id)
        accuracy = round(correct / total * 100) if total else 0
        learning, familiar, mastered = self.progress.mastery_counts(user_id)
        return (f"Answered: {total}\nCorrect: {correct}\nAccuracy: {accuracy}%\n"
                f"Due reviews: {self.due_count(user_id)}\n\n"
                f"🌱 Learning: {learning}\n📘 Familiar: {familiar}\n🏆 Mastered: {mastered}")
