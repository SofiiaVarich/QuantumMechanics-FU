from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from quantum_tutor.domain.models import Chapter, ConceptCard
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
    choice_card_ids: tuple[str, ...] = ()


class StudyService:
    def __init__(self, curriculum: CurriculumRepository, progress: ProgressRepository) -> None:
        self.curriculum = curriculum
        self.progress = progress

    def _chapters(self, chapter_number: int | None = None) -> list[Chapter]:
        chapters = self.curriculum.chapters()
        if chapter_number is None:
            return chapters
        return [chapter for chapter in chapters if chapter.number == chapter_number]

    def cards(self, chapter_number: int | None = None) -> tuple[ConceptCard, ...]:
        cards = []
        for chapter in self._chapters(chapter_number):
            cards.extend(chapter.concepts)
            for formula in chapter.formulas:
                cards.append(ConceptCard(
                    id=formula.id, section_id=str(chapter.number), front=formula.name,
                    definition=formula.when_to_use,
                    key_rule=f"{formula.equation}\nAssumptions: {'; '.join(formula.assumptions)}",
                    source_status="original_practice", source_file="",
                ))
        return tuple({card.id: card for card in cards}.values())

    @staticmethod
    def formula_text(card: ConceptCard) -> str:
        if card.formula_answer:
            return card.formula_answer
        symbols = ("=", "≥", "≤", "≈", "∝", "≠")
        for value in (card.key_rule, card.definition):
            if any(symbol in value for symbol in symbols):
                return value.split("\nAssumptions:", 1)[0].strip()
        return ""

    @classmethod
    def has_formula(cls, card: ConceptCard) -> bool:
        return bool(cls.formula_text(card))

    def mode_cards(self, chapter_number: int, mode: str = "learn") -> tuple[ConceptCard, ...]:
        cards = self.cards(chapter_number)
        if mode == "formula":
            return tuple(card for card in cards if self.has_formula(card))
        return cards

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(re.findall(r"\w+", value.casefold()))

    def set_exercise(self, card: ConceptCard, mode: str = "learn") -> Exercise:
        """Generate unique choices, excluding known overlapping concepts.

        This is a conservative equivalence filter, not symbolic math validation.
        """
        overlap_groups = (
            {"C4-016", "C4-018", "C4-022", "C3-011", "concept-c52dc23213cf6e50"},
            {"C4-023", "C4-027", "C4-040", "C4-049", "C10-016"},
            {"concept-bbf3c48cc71c54f5", "concept-09a186cab399efc8"},
            {"concept-36e0507fcc738744", "concept-7bcd3378b1235038"},
            {"C7-008", "C7-015"},
            {"C7-007", "C7-045", "C8-017", "EXP-035"},
            {"C8-021", "EXP-048", "EXP-034"},
            {"EXP-023", "EXP-044"},
            {"EXP-025", "EXP-045"},
            {"EXP-029", "EXP-046"},
        )
        blocked = {card.id}
        for group in overlap_groups:
            if card.id in group:
                blocked.update(group)
        formula_mode = self.has_formula(card)
        correct = self.formula_text(card) if formula_mode else card.definition
        prompt = (
            f"🧠 {card.front}\n\n❓ Which formula or key rule matches?"
            if formula_mode else
            f"🧠 {card.front}\n\n❓ Which meaning or application matches?"
            if mode == "law" else
            f"🧠 {card.front}\n\n❓ Which statement matches?"
        )
        normalized = self._normalized(correct)
        front = self._normalized(card.front)
        # Prefer related material, but never use another card with the same name
        # or a known synonymous meaning as a wrong alternative.
        candidates = list(self.cards())
        random.shuffle(candidates)
        candidates.sort(key=lambda other: other.section_id.split(".")[0] != card.section_id.split(".")[0])
        distractors = []
        choice_sources = {correct: card.id}
        seen = {normalized}
        for other in candidates:
            if other.id in blocked or self._normalized(other.front) == front:
                continue
            if formula_mode and not self.has_formula(other):
                continue
            value = self.formula_text(other) if formula_mode else other.definition
            key = self._normalized(value)
            if not key or key in seen:
                continue
            # Avoid obvious near-identical paraphrases and contained answers.
            words, other_words = set(normalized.split()), set(key.split())
            if key in normalized or normalized in key:
                continue
            if words and other_words and len(words & other_words) / len(words | other_words) > 0.55:
                continue
            seen.add(key)
            distractors.append(value)
            choice_sources[value] = other.id
            if len(distractors) == 3:
                break
        choices = distractors + [correct]
        random.shuffle(choices)
        answer = f"{card.definition}\n\n{card.key_rule}".strip()
        if card.formula_answer:
            answer = card.formula_answer
        for chapter in self.curriculum.chapters():
            note = chapter.content_review_required.get(card.id)
            if note:
                answer += f"\n\n🔴 Source check needed: {note}"
                break
        return Exercise(Question(card.id, "concept", prompt, answer), tuple(choices), choices.index(correct),
                                tuple(choice_sources[value] for value in choices))

    def review_cards(self, user_id: int) -> tuple[ConceptCard, ...]:
        catalog = {card.id: card for card in self.cards()}
        ids = self.progress.review_item_ids(user_id, datetime.now(timezone.utc))
        return tuple(catalog[item_id] for item_id in ids if item_id in catalog)

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
        return len(self.review_cards(user_id))

    def progress_text(self, user_id: int) -> str:
        total, correct = self.progress.statistics(user_id)
        accuracy = round(correct / total * 100) if total else 0
        learning, familiar, mastered = self.progress.mastery_counts(user_id)
        return (f"Answered: {total}\nCorrect: {correct}\nAccuracy: {accuracy}%\n"
                f"Due reviews: {self.due_count(user_id)}\n\n"
                f"🌱 Learning: {learning}\n📘 Familiar: {familiar}\n🏆 Mastered: {mastered}")
