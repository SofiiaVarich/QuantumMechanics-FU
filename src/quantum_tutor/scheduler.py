from __future__ import annotations

import logging
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from telegram.ext import Application

from quantum_tutor.presentation.handlers import main_keyboard

logger = logging.getLogger(__name__)


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
            name=f"study-reminder-{user_id}-{reminder_time.strftime('%H%M')}",
        )
        logger.info("Scheduled study reminder at %s %s", reminder_time.strftime("%H:%M"), timezone_name)


def exam_countdown(exam_date: date | None, today: date) -> str:
    if exam_date is None or exam_date < today:
        return ""
    days = (exam_date - today).days
    if days == 0:
        return "⏳ Exam today — good luck!"
    return f"⏳ {days} {'day' if days == 1 else 'days'} until the exam · {exam_date:%d.%m.%Y}"


async def send_study_reminder(context) -> None:
    data = context.application.bot_data
    today = datetime.now(ZoneInfo(data.get("timezone", "Europe/Berlin"))).date()
    countdown = exam_countdown(data.get("exam_date"), today)
    text = ("🔔 Quantum mechanics reminder\n\n"
            "A short session now: 5 min laws, 5 min formulas, and 10 min practice.")
    if countdown:
        text += f"\n\n{countdown}"
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=text,
        reply_markup=main_keyboard(context.application.bot_data.get("mini_app_url", "")),
    )
