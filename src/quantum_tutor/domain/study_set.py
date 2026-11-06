from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from quantum_tutor.domain.models import ConceptCard
from quantum_tutor.domain.spaced_repetition import ReviewRating


@dataclass
class StudySet:
    """A finite set of unique cards with a retry queue and session-local mastery."""

    cards: tuple[ConceptCard, ...]
    pending: deque[ConceptCard] = field(init=False)
    mastered: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.cards or len({card.id for card in self.cards}) != len(self.cards):
            raise ValueError("A study set requires nonempty, unique cards")
        self.pending = deque(self.cards)

    @property
    def current(self) -> ConceptCard | None:
        return self.pending[0] if self.pending else None

    @property
    def percentage(self) -> int:
        return round(100 * len(self.mastered) / len(self.cards))

    @property
    def position(self) -> int:
        return min(len(self.mastered) + 1, len(self.cards))

    def grade(self, rating: ReviewRating) -> None:
        if not self.pending:
            return
        card = self.pending.popleft()
        if rating in {"repeat", "hard"}:
            self.pending.append(card)
        else:
            self.mastered.add(card.id)
