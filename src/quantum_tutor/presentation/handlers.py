from __future__ import annotations

import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup, Update, User, WebAppInfo
from telegram.ext import ContextTypes

from quantum_tutor.application.study import StudyService
from quantum_tutor.domain.spaced_repetition import ReviewRating
from quantum_tutor.domain.study_set import StudySet
from quantum_tutor.infrastructure.curriculum import CurriculumRepository

LEARN = "🎯 Learn"
LAWS = "⚖️ Laws"
FORMULAS = "🧮 Formulas"
TOPICS = "🗂 Topics"
REVIEW = "🔁 Review"
PROGRESS = "📈 Progress"
NEXT = "➡️ Next exercise"
HOME = "🏠 Menu"
DONT_KNOW = "🔁 Don't know"
OPEN_APP = "📱 App"

# Normalize labels from previously delivered keyboards before dispatching controls.
LEGACY_CONTROL_LABELS = {
    "⚖️ Laws & Rules": LAWS,
    "🗂 Chapters & Experiments": TOPICS,
    "🏠 Main menu": HOME,
    "📱 Open Mini App": OPEN_APP,
    "🌐 Open Mini App": OPEN_APP,
    "Open Mini App": OPEN_APP,
}

SHORT_TOPIC_TITLES = {
    1: "Einführung",
    2: "Zustände & Observablen",
    5: "Drehimpuls",
    7: "Drehimpulsaddition",
    8: "Elektromagnetische Felder",
    10: "Atome, Moleküle & Quantencomputer",
    16: "Deutung der Wellenfunktion",
}

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton(LEARN)],
        [KeyboardButton(LAWS), KeyboardButton(FORMULAS)],
        [KeyboardButton(TOPICS), KeyboardButton(REVIEW)],
        [KeyboardButton(PROGRESS)],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


def main_keyboard(mini_app_url: str = "") -> ReplyKeyboardMarkup:
    if not mini_app_url:
        return MAIN_MENU
    return ReplyKeyboardMarkup(
        [[KeyboardButton(OPEN_APP)]]
        + [list(row) for row in MAIN_MENU.keyboard],
        resize_keyboard=True, is_persistent=True,
    )


def build_handlers(
    study: StudyService,
    curriculum: CurriculumRepository,
    allowed_user_ids: tuple[int, ...],
    mini_app_url: str = "",
    *,
    public_access: bool = False,
):
    main_menu = main_keyboard(mini_app_url)
    chapters = curriculum.chapters()
    digits = ("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣")
    number_emojis = tuple(
        "🔟" if number == 10 else "".join(digits[int(digit)] for digit in str(number))
        for number in range(1, max((chapter.number for chapter in chapters), default=0) + 1)
    )
    previous_topic_labels = {
        (
            f"📖 Chapter {number_emojis[chapter.number - 1]} · {chapter.title_de}"
            if chapter.professor == "Eisert"
            else f"🔬 Experiment · {chapter.title_de} · {chapter.date or 'Termin offen'}"
        ): chapter.number
        for chapter in chapters
    }
    # Previously delivered reply keyboards remain clickable after a display rename.
    legacy_topic_labels = {
        (
            f"{number_emojis[chapter.number - 1]} {chapter.title_de}"
            if chapter.professor == "Eisert"
            else f"🔬 {chapter.date or 'Termin offen'} · {chapter.title_de}"
        ): chapter.number
        for chapter in chapters
    }
    experiments = [chapter for chapter in chapters if chapter.professor != "Eisert"]
    experiment_numbers = {chapter.number: index for index, chapter in enumerate(experiments, 1)}
    topic_labels = {
        (
            f"📖 {number_emojis[chapter.number - 1]} · {SHORT_TOPIC_TITLES.get(chapter.number, chapter.title_de)}"
            if chapter.professor == "Eisert"
            else f"🔬 E{experiment_numbers[chapter.number]} · {SHORT_TOPIC_TITLES.get(chapter.number, chapter.title_de)}"
        ): chapter.number
        for chapter in chapters
    }
    selectable_labels = {**legacy_topic_labels, **previous_topic_labels, **topic_labels}
    experiment_dates = "\n".join(
        f"E{experiment_numbers[chapter.number]} · {chapter.title_de} · {chapter.date or 'Termin offen'}"
        for chapter in experiments
    )
    section_labels = {
        f"{section.id} {section.title}": (chapter.number, section)
        for chapter in chapters
        for section in chapter.sections
    }
    topic_actions_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton(LEARN)],
            [KeyboardButton(LAWS), KeyboardButton(FORMULAS)],
            [KeyboardButton(TOPICS), KeyboardButton(HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

    def message_and_user(update: Update) -> tuple[Message, User]:
        message, user = update.effective_message, update.effective_user
        if message is None or user is None:
            raise RuntimeError("Handler received an update without a message or user")
        return message, user

    async def reject_if_unauthorized(update: Update) -> bool:
        user = update.effective_user
        chat = update.effective_chat
        if chat is None or chat.type != "private":
            if update.effective_message is not None:
                await update.effective_message.reply_text("🔒 Please use this bot in a private chat.")
            return True
        if (user is not None and type(user.id) is int and user.id > 0
                and (public_access or user.id in allowed_user_ids)):
            return False
        if update.effective_message is not None:
            await update.effective_message.reply_text("🔒 This is a private study bot.")
        return True

    async def send_app_launcher(message: Message) -> None:
        if not mini_app_url:
            await message.reply_text("The Mini App address has not been configured yet.")
            return
        await message.reply_text(
            "📱 Open Quantum Tutor securely inside Telegram:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(OPEN_APP, web_app=WebAppInfo(mini_app_url)),
            ]]),
        )

    async def send_menu(message: Message, text: str = "✨ What would you like to study?") -> None:
        await message.reply_text(text, reply_markup=main_menu)

    def progress_label(ids: set[str], known: set[str]) -> str:
        if not ids:
            return "— no cards"
        return f"{round(100 * len(ids & known) / len(ids))}%"

    async def show_topics(message: Message, user_id: int, study_mode: str = "learn") -> None:
        known = study.progress.known_item_ids(user_id)
        labels = []
        for label, number in topic_labels.items():
            ids = {card.id for card in study.mode_cards(number, study_mode)}
            labels.append(f"{label} · {progress_label(ids, known)}")
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(label)] for label in labels] + [[KeyboardButton(HOME)]],
            resize_keyboard=True, is_persistent=True,
        )
        await message.reply_text(
            f"{ {'learn': LEARN, 'formula': FORMULAS, 'law': LAWS}.get(study_mode, TOPICS)} · Choose a chapter or experiment\n\n"
            "📖 Chapters 1️⃣–🔟 · Eisert\n🔬 Experiments · Franke\n\n"
            f"{experiment_dates}\n\nSelect one entry to start its full card set.",
            reply_markup=keyboard,
        )

    async def choose_mode(
        message: Message, context: ContextTypes.DEFAULT_TYPE, user_id: int, study_mode: str
    ) -> None:
        if context.user_data is None:
            return
        for key in ("study_set", "question", "exercise", "concept_choices", "mode", "selected_chapter"):
            context.user_data.pop(key, None)
        context.user_data["viewer_id"] = user_id
        context.user_data["requested_mode"] = study_mode
        await show_topics(message, user_id, study_mode)

    async def select_topic(
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        chapter_number: int,
    ) -> None:
        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        context.user_data["selected_chapter"] = chapter_number
        context.user_data.pop("study_set", None)
        context.user_data.pop("question", None)
        context.user_data["session_index"] = 1
        chapter = curriculum.chapter(chapter_number)
        if chapter is None:
            await show_topics(message, int(context.user_data.get("viewer_id", 0)))
            return
        study_mode = context.user_data.get("requested_mode", "learn")
        cards = study.mode_cards(chapter_number, study_mode)
        if not cards:
            await message.reply_text("No cards are available for this topic in the selected mode yet.")
            await show_topics(message, int(context.user_data.get("viewer_id", 0)), study_mode)
            return
        context.user_data["set_kind"] = "topic"
        context.user_data["session_mode"] = study_mode
        context.user_data["study_set"] = StudySet(cards)
        context.user_data.pop("exercise", None)
        await message.reply_text(f"📖 {chapter.title_de} · {len(cards)} cards")
        await present_set_card(message, context)

    async def present_set_card(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.user_data is None:
            return
        session: StudySet | None = context.user_data.get("study_set")
        if session is None:
            return
        card = session.current
        if card is None:
            await message.reply_text(
                f"✅ Set complete · {len(session.cards)}/{len(session.cards)}\n"
                "100% completed in this set.\n"
                "This is recognition practice, not long-term or exam mastery.",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton(HOME)]], resize_keyboard=True, is_persistent=True,
                ),
            )
            context.user_data.pop("study_set", None)
            context.user_data.pop("question", None)
            context.user_data.pop("mode", None)
            context.user_data.pop("concept_choices", None)
            context.user_data.pop("requested_mode", None)
            context.user_data.pop("selected_chapter", None)
            return
        exercise = study.set_exercise(card, context.user_data.get("session_mode", "learn"))
        context.user_data["question"] = exercise.question
        context.user_data["concept_choices"] = {
            f"{index + 1}️⃣ {choice}": index == exercise.correct_index
            for index, choice in enumerate(exercise.choices)
        }
        context.user_data["mode"] = "concept_choice"
        context.user_data["presented_at"] = time.monotonic()
        await message.reply_text(
            f"📖 {session.position}/{len(session.cards)} · {session.percentage}% completed in this set\n\n"
            + exercise.question.prompt,
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(label)] for label in context.user_data["concept_choices"]]
                + [
                    [KeyboardButton(DONT_KNOW)],
                    [KeyboardButton(HOME)],
                ],
                resize_keyboard=True, is_persistent=True,
            ),
        )

    async def show_review(message: Message, user: User, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.user_data is None:
            return
        cards = study.review_cards(user.id)
        if not cards:
            await send_menu(message, "✅ No missed or due cards to review right now.")
            return
        context.user_data["viewer_id"] = user.id
        context.user_data.pop("selected_chapter", None)
        context.user_data.pop("exercise", None)
        context.user_data["set_kind"] = "review"
        context.user_data["session_mode"] = "learn"
        context.user_data["requested_mode"] = "learn"
        context.user_data["study_set"] = StudySet(cards)
        await message.reply_text(f"🔁 Review · {len(cards)} cards from all topics")
        await present_set_card(message, context)

    async def show_progress(message: Message, user: User) -> None:
        await message.reply_text(
            "📈 Your learning progress\n\n" + study.progress_text(user.id),
            reply_markup=main_menu,
        )

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, user = message_and_user(update)
        if (getattr(message, "text", None) or "").split("@", 1)[0].split()[0:1] == ["/app"]:
            await send_app_launcher(message)
            return
        if context.user_data is not None:
            context.user_data.clear()
            context.user_data["viewer_id"] = user.id
        await send_menu(message, "👋✨ Welcome to Quantum Tutor! Choose a learning mode below.")

    async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await choose_mode(message, context, user.id, "learn")

    async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await choose_mode(message, context, user.id, "learn")

    async def laws(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await choose_mode(message, context, user.id, "law")

    async def formulas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await choose_mode(message, context, user.id, "formula")

    async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await show_review(message, user, context)

    async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await show_progress(message, user)

    async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, user = message_and_user(update)
        text = message.text or ""
        text = LEGACY_CONTROL_LABELS.get(text, text)
        if text == OPEN_APP:
            await send_app_launcher(message)
            return
        if context.user_data is not None:
            context.user_data["viewer_id"] = user.id
        # Old keyboard percentages may be stale after another answer; route by stable label.
        if " · " in text:
            base = text.rsplit(" · ", 1)[0]
            if base in selectable_labels or base in section_labels:
                text = base
        if text in {HOME, TOPICS, LEARN, LAWS, FORMULAS} and context.user_data is not None:
            context.user_data.pop("study_set", None)
            context.user_data.pop("question", None)
            context.user_data.pop("mode", None)

        if text in {HOME, "/start"}:
            if context.user_data is not None:
                context.user_data.clear()
                context.user_data["viewer_id"] = user.id
            await send_menu(message)
        elif text in selectable_labels:
            await select_topic(message, context, selectable_labels[text])
        elif text in section_labels:
            chapter_number, section = section_labels[text]
            if context.user_data is not None:
                context.user_data["selected_chapter"] = chapter_number
                context.user_data["selected_section"] = section.id
            chapter = curriculum.chapter(chapter_number)
            cards = [
                card for card in chapter.concepts
                if card.section_id == section.id or card.section_id.startswith(section.id + ".")
            ] if chapter else []
            if cards and context.user_data is not None:
                context.user_data["study_set"] = StudySet(tuple(cards))
                context.user_data.pop("exercise", None)
                await present_set_card(message, context)
            else:
                await message.reply_text(
                    f"📖 {section.id} {section.title}\np. {section.page}\n\n"
                    "Section-specific lessons are not available yet.\n"
                    "The learning buttons below practice the whole chapter.",
                    reply_markup=topic_actions_keyboard,
                )
        elif text == LEARN:
            await choose_mode(message, context, user.id, "learn")
        elif text == NEXT:
            if context.user_data is not None and context.user_data.get("study_set") is not None:
                await present_set_card(message, context)
            else:
                await choose_mode(message, context, user.id, "learn")
        elif text == LAWS:
            await choose_mode(message, context, user.id, "law")
        elif text == FORMULAS:
            await choose_mode(message, context, user.id, "formula")
        elif text == TOPICS:
            await choose_mode(message, context, user.id, "learn")
        elif text == REVIEW:
            await show_review(message, user, context)
        elif text == PROGRESS:
            await show_progress(message, user)
        elif context.user_data is not None and context.user_data.get("mode") == "concept_choice":
            choices = context.user_data.get("concept_choices", {})
            if text != DONT_KNOW and text not in choices:
                await message.reply_text("Choose an answer below, or tap Don't know.")
                return
            question = context.user_data.get("question")
            session = context.user_data.get("study_set")
            if question is None or session is None:
                await send_menu(message, "This set expired. Choose a topic again.")
                return
            correct = text != DONT_KNOW and choices[text]
            rating: ReviewRating = "okay" if correct else "repeat"
            started = context.user_data.get("presented_at", time.monotonic())
            study.record(
                user.id, question, correct, rating=rating,
                response_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
            session.grade(rating)
            context.user_data.pop("question", None)
            context.user_data.pop("concept_choices", None)
            result = "✅ Correct" if correct else "❌ Review this card again later"
            await message.reply_text(f"{result}\n\n{question.answer}")
            await present_set_card(message, context)
        else:
            await send_menu(message, "🤔 I did not recognize that. Please choose a button below.")

    return start, topics, learn, laws, formulas, review, progress, text_input
