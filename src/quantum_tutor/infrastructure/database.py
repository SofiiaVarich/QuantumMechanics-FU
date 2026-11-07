from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from quantum_tutor.domain.models import ReviewState


class ProgressRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
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
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(answers)").fetchall()
            }
            migrations = {
                "rating": "ALTER TABLE answers ADD COLUMN rating TEXT",
                "response_ms": "ALTER TABLE answers ADD COLUMN response_ms INTEGER",
                "scheduler_version": (
                    "ALTER TABLE answers ADD COLUMN scheduler_version INTEGER NOT NULL DEFAULT 1"
                ),
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

    def save_answer(
        self,
        state: ReviewState,
        correct: bool,
        rating: str | None = None,
        response_ms: int | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO answers(
                    user_id, item_id, correct, rating, response_ms, scheduler_version
                ) VALUES (?, ?, ?, ?, ?, 2)""",
                (state.user_id, state.item_id, int(correct), rating, response_ms),
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

    def review_item_ids(self, user_id: int, now: datetime) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT item_id FROM reviews WHERE user_id=?
                AND (repetitions=0 OR due_at<=?) ORDER BY due_at, item_id""",
                (user_id, now.isoformat()),
            ).fetchall()
        return [str(row["item_id"]) for row in rows]

    def known_item_ids(self, user_id: int) -> set[str]:
        """Latest correct recognition/recall, not a claim of durable mastery."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT item_id FROM reviews WHERE user_id=? AND repetitions>0",
                (user_id,),
            ).fetchall()
        return {str(row["item_id"]) for row in rows}

    def chapter_statistics(self, user_id: int, item_ids: list[str]) -> tuple[int, int]:
        """Return (total, correct) statistics for a specific set of item IDs."""
        if not item_ids:
            return 0, 0
        placeholders = ",".join("?" for _ in item_ids)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) total, COALESCE(SUM(correct), 0) correct FROM answers WHERE user_id=? AND item_id IN ({placeholders})",
                (user_id, *item_ids),
            ).fetchone()
        return int(row["total"]), int(row["correct"])

    def mastery_counts(self, user_id: int, item_ids: list[str] | None = None) -> tuple[int, int, int]:
        """Return counts for learning, familiar, and mastered reviewed items."""
        query = "SELECT repetitions, COUNT(*) count FROM reviews WHERE user_id=?"
        params: list[Any] = [user_id]
        if item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            query += f" AND item_id IN ({placeholders})"
            params.extend(item_ids)
        query += " GROUP BY repetitions"
        
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        learning = sum(int(row["count"]) for row in rows if int(row["repetitions"]) < 2)
        familiar = sum(int(row["count"]) for row in rows if 2 <= int(row["repetitions"]) < 4)
        mastered = sum(int(row["count"]) for row in rows if int(row["repetitions"]) >= 4)
        return learning, familiar, mastered

    def statistics(self, user_id: int) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) total, COALESCE(SUM(correct), 0) correct FROM answers WHERE user_id=?",
                (user_id,),
            ).fetchone()
        return int(row["total"]), int(row["correct"])
