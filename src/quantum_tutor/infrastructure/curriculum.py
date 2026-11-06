from __future__ import annotations

import json
from pathlib import Path

from quantum_tutor.domain.models import Chapter


class CurriculumRepository:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def chapters(self) -> list[Chapter]:
        paths = sorted(self.directory.glob("topic_*.json"))
        if not paths:
            paths = sorted(self.directory.glob("chapter_*.json"))
        chapters = [self._load(path) for path in paths]
        return sorted(chapters, key=lambda chapter: chapter.number)

    def chapter(self, number: int) -> Chapter | None:
        return next((chapter for chapter in self.chapters() if chapter.number == number), None)

    def _load(self, path: Path) -> Chapter:
        with path.open(encoding="utf-8") as source:
            return Chapter.from_dict(json.load(source))
