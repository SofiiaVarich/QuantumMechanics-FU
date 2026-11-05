from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from quantum_tutor.domain.models import ReviewState


class ProgressRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS reviews (
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    interval_days INTEGER NOT NULL,
                    repetitions INTEGER NOT NULL,
                    due_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, item_id)
                );
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    answered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_answer(self, state: ReviewState, correct: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO answers(user_id, item_id, correct) VALUES (?, ?, ?)",
                (state.user_id, state.item_id, int(correct)),
            )
            connection.execute(
                """INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET
                    item_type=excluded.item_type,
                    interval_days=excluded.interval_days,
                    repetitions=excluded.repetitions,
                    due_at=excluded.due_at""",
                (state.user_id, state.item_id, state.item_type, state.interval_days,
                 state.repetitions, state.due_at.isoformat()),
            )

    def repetition_count(self, user_id: int, item_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT repetitions FROM reviews WHERE user_id=? AND item_id=?",
                (user_id, item_id),
            ).fetchone()
        return int(row["repetitions"]) if row else 0

    def due_item_ids(self, user_id: int, now: datetime) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT item_id FROM reviews WHERE user_id=? AND due_at<=? ORDER BY due_at",
                (user_id, now.isoformat()),
            ).fetchall()
        return [str(row["item_id"]) for row in rows]

    def statistics(self, user_id: int) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) total, COALESCE(SUM(correct), 0) correct FROM answers WHERE user_id=?",
                (user_id,),
            ).fetchone()
        return int(row["total"]), int(row["correct"])
