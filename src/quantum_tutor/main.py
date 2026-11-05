from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

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
    start, topics, terms, formulas, review, stats, callback = build_handlers(
        study, curriculum, settings.allowed_user_id
    )

    async def configure_bot(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Open the clickable study menu"),
            BotCommand("topics", "Browse course chapters"),
            BotCommand("terms", "Practice German-English terminology"),
            BotCommand("formulas", "Practice formula recall"),
            BotCommand("review", "Show due reviews"),
            BotCommand("progress", "Show learning statistics"),
        ])

    application = (Application.builder().token(settings.telegram_token)
                   .post_init(configure_bot).build())
    for name, handler in (("start", start), ("topics", topics), ("terms", terms),
                          ("formulas", formulas), ("review", review), ("progress", stats)):
        application.add_handler(CommandHandler(name, handler))
    application.add_handler(CallbackQueryHandler(callback))
    schedule_reminders(
        application,
        settings.allowed_user_id,
        settings.timezone,
        parse_reminder_times(settings.reminder_times),
    )
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    create_application(Settings.from_env()).run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
