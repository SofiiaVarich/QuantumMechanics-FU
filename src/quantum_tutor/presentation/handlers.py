from __future__ import annotations

import time

from telegram import KeyboardButton, Message, ReplyKeyboardMarkup, Update, User
from telegram.ext import ContextTypes

from quantum_tutor.application.study import Exercise, Question, StudyService
from quantum_tutor.domain.spaced_repetition import ReviewRating
from quantum_tutor.infrastructure.curriculum import CurriculumRepository

LEARN = "🎯 Learn"
LAWS = "⚖️ Laws & Rules"
FORMULAS = "🧮 Formulas"
TOPICS = "🗂 Topics"
REVIEW = "🔁 Review"
PROGRESS = "📈 Progress"
REVEAL = "👀 Reveal answer"
REPEAT = "🔁 Repeat"
HARD = "🟠 Hard"
OKAY = "🔵 Okay"
EASY = "🟢 Easy"
NEXT = "➡️ Next exercise"
HOME = "🏠 Main menu"

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


def build_handlers(
    study: StudyService,
    curriculum: CurriculumRepository,
    allowed_user_ids: tuple[int, ...],
):
    chapters = curriculum.chapters()
    number_emojis = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
    topic_labels = {
        f"{number_emojis[chapter.number - 1]} {chapter.title_de}": chapter.number
        for chapter in chapters
    }
    topics_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(label)] for label in topic_labels] + [[KeyboardButton(HOME)]],
        resize_keyboard=True,
        is_persistent=True,
    )
    topic_actions_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton(LEARN)],
            [KeyboardButton(LAWS), KeyboardButton(FORMULAS)],
            [KeyboardButton(TOPICS), KeyboardButton(HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

    def selected_chapter(context: ContextTypes.DEFAULT_TYPE) -> int | None:
        if context.user_data is None:
            return None
        value = context.user_data.get("selected_chapter")
        return int(value) if value is not None else None

    def message_and_user(update: Update) -> tuple[Message, User]:
        message, user = update.effective_message, update.effective_user
        if message is None or user is None:
            raise RuntimeError("Handler received an update without a message or user")
        return message, user

    async def reject_if_unauthorized(update: Update) -> bool:
        user = update.effective_user
        if user is not None and user.id in allowed_user_ids:
            return False
        if update.effective_message is not None:
            await update.effective_message.reply_text("🔒 This is a private study bot.")
        return True

    async def send_menu(message: Message, text: str = "✨ What would you like to study?") -> None:
        await message.reply_text(text, reply_markup=MAIN_MENU)

    async def show_topics(message: Message) -> None:
        await message.reply_text(
            "🗂✨ Themen auswählen\n\nTippe unten auf ein Kapitel, um nur Material aus diesem Thema zu lernen.",
            reply_markup=topics_keyboard,
        )

    async def select_topic(
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        chapter_number: int,
    ) -> None:
        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        context.user_data["selected_chapter"] = chapter_number
        context.user_data["session_index"] = 1
        chapter = curriculum.chapter(chapter_number)
        if chapter is None:
            await show_topics(message)
            return
        laws = study.item_count("law", chapter_number)
        if laws == 0:
            text = (
                f"{number_emojis[chapter_number - 1]} {chapter.title_de}\n\n"
                "⚠️ Für dieses Kapitel gibt es noch keine geprüften Lernkarten.\n"
                "Du kannst ein anderes Thema auswählen."
            )
        else:
            text = (
                f"{number_emojis[chapter_number - 1]} {chapter.title_de}\n\n"
                f"⚖️ Gesetze und Formeln: {laws}\n\n"
                "Wähle jetzt einen Lernmodus. Alle Fragen bleiben in diesem Kapitel."
            )
        await message.reply_text(text, reply_markup=topic_actions_keyboard)

    async def show_review(message: Message, user: User) -> None:
        await message.reply_text(
            f"🔁 Review queue\n\nYou have {study.due_count(user.id)} item(s) due.",
            reply_markup=MAIN_MENU,
        )

    async def show_progress(message: Message, user: User) -> None:
        await message.reply_text(
            "📈 Your learning progress\n\n" + study.progress_text(user.id),
            reply_markup=MAIN_MENU,
        )

    async def send_exercise(
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        item_type: str | None = None,
        reset: bool = False,
    ) -> None:
        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        if reset:
            context.user_data["session_index"] = 1
        chapter_number = selected_chapter(context)
        exercise = study.adaptive_exercise(item_type, chapter_number)
        if exercise is None:
            await message.reply_text("⚠️ Für dieses Kapitel sind noch keine geprüften Formeln verfügbar.", reply_markup=topics_keyboard)
            return
        category = exercise.question.item_type
        context.user_data["exercise"] = exercise
        context.user_data["exercise_attempts"] = 0
        context.user_data["mode"] = "exercise"
        context.user_data["presented_at"] = time.monotonic()
        context.user_data["session_category"] = category
        index = int(context.user_data.get("session_index", 1))
        total = study.item_count(category, chapter_number)
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(f"{index + 1}️⃣ {choice}")] for index, choice in enumerate(exercise.choices)]
            + [[KeyboardButton(HOME)]],
            resize_keyboard=True,
            is_persistent=True,
            one_time_keyboard=False,
        )
        await message.reply_text(
            f"🎯✨ Adaptive {category} exercise  •  {index}/{total}\n\n"
            f"{exercise.question.prompt}",
            reply_markup=keyboard,
        )

    async def ask_flashcard(
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        kind: str,
        reset: bool = False,
    ) -> None:
        chapter_number = selected_chapter(context)
        question = (
            study.random_law(chapter_number)
            if kind == "law"
            else study.random_formula(chapter_number)
        )
        if question is None:
            await message.reply_text("⚠️ No study material is available yet.", reply_markup=MAIN_MENU)
            return
        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        if reset or context.user_data.get("session_category") != kind:
            context.user_data["session_index"] = 1
        context.user_data["question"] = question
        context.user_data["mode"] = "flashcard"
        context.user_data["presented_at"] = time.monotonic()
        context.user_data["session_category"] = kind
        index = int(context.user_data.get("session_index", 1))
        total = study.item_count(kind, chapter_number)
        icon = "⚖️📜" if kind == "law" else "🧮📐"
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(REVEAL)], [KeyboardButton(HOME)]],
            resize_keyboard=True,
            is_persistent=True,
        )
        await message.reply_text(
            f"{icon} {kind.title()} recall  •  {index}/{total}\n\n{question.prompt}",
            reply_markup=keyboard,
        )

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, _ = message_and_user(update)
        if context.user_data is not None:
            context.user_data.pop("selected_chapter", None)
        await send_menu(message, "👋✨ Welcome to Quantum Tutor! Choose a learning mode below.")

    async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await show_topics(message_and_user(update)[0])

    async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await send_exercise(message_and_user(update)[0], context, reset=True)

    async def laws(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await ask_flashcard(message_and_user(update)[0], context, "law", reset=True)

    async def formulas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await ask_flashcard(message_and_user(update)[0], context, "formula", reset=True)

    async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await show_review(message, user)

    async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            message, user = message_and_user(update)
            await show_progress(message, user)

    async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, user = message_and_user(update)
        text = message.text or ""

        if text in {HOME, "/start"}:
            if context.user_data is not None:
                context.user_data.pop("selected_chapter", None)
            await send_menu(message)
        elif text in topic_labels:
            await select_topic(message, context, topic_labels[text])
        elif text == LEARN:
            await send_exercise(message, context, reset=True)
        elif text == NEXT:
            category = context.user_data.get("session_category") if context.user_data else None
            await send_exercise(message, context, category)
        elif text == LAWS:
            await ask_flashcard(message, context, "law", reset=True)
        elif text == FORMULAS:
            await ask_flashcard(message, context, "formula", reset=True)
        elif text == TOPICS:
            await show_topics(message)
        elif text == REVIEW:
            await show_review(message, user)
        elif text == PROGRESS:
            await show_progress(message, user)
        elif text == REVEAL:
            await reveal_flashcard(message, context)
        elif text in {REPEAT, HARD, OKAY, EASY}:
            ratings: dict[str, ReviewRating] = {
                REPEAT: "repeat", HARD: "hard", OKAY: "okay", EASY: "easy"
            }
            await grade_flashcard(message, context, user, ratings[text])
        elif context.user_data is not None and context.user_data.get("mode") == "exercise":
            await grade_exercise(message, context, user, text)
        else:
            await send_menu(message, "🤔 I did not recognize that. Please choose a button below.")

    async def reveal_flashcard(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.user_data is None:
            return
        question: Question | None = context.user_data.get("question")
        if question is None:
            await send_menu(message, "⌛ This card expired. Choose another activity.")
            return
        context.user_data["mode"] = "grading"
        keyboard = ReplyKeyboardMarkup(
            [KeyboardButton(REPEAT), KeyboardButton(HARD)],
            [KeyboardButton(OKAY), KeyboardButton(EASY)],
            [KeyboardButton(HOME)],
            resize_keyboard=True,
            is_persistent=True,
        )
        category = context.user_data.get("session_category")
        icon = "⚖️📜" if category == "law" else "📊🧮"
        await message.reply_text(f"{icon} Answer\n\n{question.answer}", reply_markup=keyboard)

    async def grade_flashcard(
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        user: User,
        rating: ReviewRating,
    ) -> None:
        if context.user_data is None:
            return
        question: Question | None = context.user_data.pop("question", None)
        category = str(context.user_data.get("session_category", "formula"))
        context.user_data.pop("mode", None)
        if question is None:
            await send_menu(message, "⌛ This card expired.")
            return
        correct = rating != "repeat"
        started = float(context.user_data.pop("presented_at", time.monotonic()))
        response_ms = max(0, round((time.monotonic() - started) * 1000))
        study.record(user.id, question, correct, rating=rating, response_ms=response_ms)
        status_by_rating = {
            "repeat": "🔁 It will return in about 10 minutes.",
            "hard": "🟠 Kept at a short interval for more practice.",
            "okay": "🔵 Good recall — advanced one review stage.",
            "easy": "🟢 Strong recall — advanced two review stages.",
        }
        status = status_by_rating[rating]
        await message.reply_text(status)
        chapter_number = selected_chapter(context)
        total = max(study.item_count(category, chapter_number), 1)
        current = int(context.user_data.get("session_index", 1))
        context.user_data["session_index"] = current % total + 1
        await ask_flashcard(message, context, category)

    async def grade_exercise(
        message: Message, context: ContextTypes.DEFAULT_TYPE, user: User, text: str
    ) -> None:
        if context.user_data is None:
            return
        exercise: Exercise | None = context.user_data.get("exercise")
        if exercise is None:
            await send_menu(message, "⌛ This exercise expired.")
            return
        try:
            selected_index = int(text[0]) - 1
        except (ValueError, IndexError):
            await message.reply_text("👆 Please choose one of the answer buttons below.")
            return
        if selected_index < 0 or selected_index >= len(exercise.choices):
            return
        correct = selected_index == exercise.correct_index
        started = float(context.user_data.pop("presented_at", time.monotonic()))
        response_ms = max(0, round((time.monotonic() - started) * 1000))
        rating = "okay" if correct else "repeat"
        study.record(
            user.id,
            exercise.question,
            correct,
            rating=rating,
            response_ms=response_ms,
        )
        if not correct:
            attempts = int(context.user_data.get("exercise_attempts", 0)) + 1
            context.user_data["exercise_attempts"] = attempts
            context.user_data["presented_at"] = time.monotonic()
            hint = "\n💡 Read the situation once more." if attempts >= 2 else ""
            await message.reply_text(
                f"❌ Not correct yet. Try the same question again.{hint}"
            )
            return

        context.user_data.pop("exercise", None)
        context.user_data.pop("exercise_attempts", None)
        context.user_data.pop("mode", None)
        await message.reply_text(f"✅ Correct\n\n{exercise.question.answer}")
        category = exercise.question.item_type
        chapter_number = selected_chapter(context)
        total = max(study.item_count(category, chapter_number), 1)
        current = int(context.user_data.get("session_index", 1))
        context.user_data["session_index"] = current % total + 1
        await send_exercise(message, context, category)

    return start, topics, learn, laws, formulas, review, progress, text_input
