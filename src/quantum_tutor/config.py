from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    database_path: Path
    curriculum_path: Path
    allowed_user_ids: tuple[int, ...]
    timezone: str
    reminder_times: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and set it.")
        user_ids = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").strip()
        if not user_ids:
            user_ids = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
        if not user_ids:
            raise RuntimeError("TELEGRAM_ALLOWED_USER_IDS is missing from .env")
        try:
            allowed_user_ids = tuple(
                int(value.strip()) for value in user_ids.split(",") if value.strip()
            )
        except ValueError as error:
            raise RuntimeError(
                "TELEGRAM_ALLOWED_USER_IDS must contain comma-separated numeric IDs"
            ) from error
        if not allowed_user_ids:
            raise RuntimeError("At least one Telegram user ID is required")
        return cls(
            telegram_token=token,
            database_path=Path(os.getenv("DATABASE_PATH", "quantum_tutor.db")),
            curriculum_path=Path(os.getenv("CURRICULUM_PATH", "curriculum")),
            allowed_user_ids=allowed_user_ids,
            timezone=os.getenv("TZ", "Europe/Berlin"),
            reminder_times=os.getenv("REMINDER_TIMES", "05:30,20:00"),
        )
