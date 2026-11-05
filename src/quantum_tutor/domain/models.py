from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Term:
    id: str
    german: str
    english: str
    definition: str


@dataclass(frozen=True)
class Formula:
    id: str
    name: str
    name_de: str
    equation: str
    symbols: dict[str, str]
    when_to_use: str
    assumptions: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    title_de: str
    professor: str
    date: str | None = None
    source_url: str = ""
    terms: tuple[Term, ...] = ()
    formulas: tuple[Formula, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chapter":
        return cls(
            number=data["number"],
            title=data["title"],
            title_de=data.get("title_de", data["title"]),
            professor=data.get("professor", "Eisert"),
            date=data.get("date"),
            source_url=data.get("source_url", ""),
            terms=tuple(Term(**item) for item in data.get("terms", [])),
            formulas=tuple(Formula(**item) for item in data.get("formulas", [])),
        )


@dataclass(frozen=True)
class ReviewState:
    user_id: int
    item_id: str
    item_type: str
    interval_days: int
    repetitions: int
    due_at: datetime

    @property
    def is_due(self) -> bool:
        return self.due_at <= datetime.now(timezone.utc)
