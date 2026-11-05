from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

logger = logging.getLogger(__name__)

REMINDER_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📚 Study terms", callback_data="menu:terms"),
        InlineKeyboardButton("🧮 Practice formulas", callback_data="menu:formulas"),
    ],
    [InlineKeyboardButton("📈 Show progress", callback_data="menu:progress")],
])


def parse_reminder_times(value: str) -> tuple[time, ...]:
    """Parse comma-separated 24-hour times such as ``05:30,20:00``."""
    parsed: list[time] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            hour_text, minute_text = item.split(":", maxsplit=1)
            hour, minute = int(hour_text), int(minute_text)
            parsed.append(time(hour=hour, minute=minute))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid reminder time {item!r}; expected HH:MM") from error
    if not parsed:
        raise ValueError("At least one reminder time is required")
    return tuple(parsed)


def schedule_reminders(
    application: Application,
    user_id: int,
    timezone_name: str,
    reminder_times: tuple[time, ...],
) -> None:
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError("JobQueue is unavailable; install python-telegram-bot[job-queue]")

    timezone = ZoneInfo(timezone_name)
    for reminder_time in reminder_times:
        localized_time = reminder_time.replace(tzinfo=timezone)
        job_queue.run_daily(
            send_study_reminder,
            time=localized_time,
            chat_id=user_id,
            user_id=user_id,
            name=f"study-reminder-{reminder_time.strftime('%H%M')}",
        )
        logger.info("Scheduled study reminder at %s %s", reminder_time.strftime("%H:%M"), timezone_name)


async def send_study_reminder(context) -> None:
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=("🔔 Quantum mechanics reminder\n\n"
              "A short session now: 5 min terminology, 5 min formulas, "
              "and 10 min practice. This is a personal study reminder, not an official FU notice."),
        reply_markup=REMINDER_MENU,
    )
