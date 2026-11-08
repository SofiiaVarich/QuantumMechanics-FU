from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from quantum_tutor.domain.models import Chapter


class CurriculumRepository:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def chapters(self) -> list[Chapter]:
        paths = sorted(self.directory.glob("topic_*.json"))

        chapters = [self._load(path) for path in paths]
        return sorted(chapters, key=lambda chapter: chapter.number)

    def chapter(self, number: int) -> Chapter | None:
        return next((chapter for chapter in self.chapters() if chapter.number == number), None)

    def _load(self, path: Path) -> Chapter:
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        chapter = Chapter.from_dict(data)
        metadata = data.get("concept_metadata", {})
        concepts = []
        for card in chapter.concepts:
            rendering = metadata.get(card.id, {})
            # Legacy formula_latex may be a broader expression or another rule.
            # Only an explicit exact-text pair is eligible for answer rendering.
            if (not card.formula_answer_latex and card.formula_answer
                    and rendering.get("formula_answer") == card.formula_answer
                    and rendering.get("formula_answer_latex")):
                card = replace(card, formula_answer_latex=rendering["formula_answer_latex"])
            concepts.append(card)
        return replace(chapter, concepts=tuple(concepts))
