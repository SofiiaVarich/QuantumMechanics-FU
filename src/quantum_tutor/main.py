from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from quantum_tutor.application.study import StudyService
from quantum_tutor.config import Settings
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.presentation.handlers import build_handlers
from quantum_tutor.scheduler import parse_reminder_times, schedule_reminders


def create_application(settings: Settings) -> Application:
    curriculum = CurriculumRepository(settings.curriculum_path)
    progress = ProgressRepository(settings.database_path)
    study = StudyService(curriculum, progress)
    start, topics, learn, laws, formulas, review, stats, text_input = build_handlers(
        study, curriculum, settings.allowed_user_ids
    )

    async def configure_bot(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Open the clickable study menu"),
            BotCommand("learn", "Start adaptive exercises"),
            BotCommand("topics", "Browse course chapters"),
            BotCommand("laws", "Learn physical laws and their meaning"),
            BotCommand("formulas", "Practice formula recall"),
            BotCommand("review", "Show due reviews"),
            BotCommand("progress", "Show learning statistics"),
        ])

    application = (
        Application.builder()
        .token(settings.telegram_token)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(60)
        .post_init(configure_bot)
        .build()
    )
    for name, handler in (("start", start), ("topics", topics), ("learn", learn), ("laws", laws),
                          ("formulas", formulas), ("review", review), ("progress", stats)):
        application.add_handler(CommandHandler(name, handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))
    reminder_times = parse_reminder_times(settings.reminder_times)
    for user_id in settings.allowed_user_ids:
        schedule_reminders(
            application,
            user_id,
            settings.timezone,
            reminder_times,
        )
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    create_application(Settings.from_env()).run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
