from __future__ import annotations

import random
import time

from telegram import KeyboardButton, Message, ReplyKeyboardMarkup, Update, User
from telegram.ext import ContextTypes

from quantum_tutor.application.study import Exercise, Question, StudyService
from quantum_tutor.domain.spaced_repetition import ReviewRating
from quantum_tutor.domain.study_set import StudySet
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
DONT_KNOW = "🔁 Don't know"
KNOW = "✅ Know"

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
    digits = ("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣")
    number_emojis = tuple(
        "🔟" if number == 10 else "".join(digits[int(digit)] for digit in str(number))
        for number in range(1, max((chapter.number for chapter in chapters), default=0) + 1)
    )
    topic_labels = {
        (
            f"{number_emojis[chapter.number - 1]} {chapter.title_de}"
            if chapter.professor == "Eisert"
            else f"🔬 {chapter.date or 'Termin offen'} · {chapter.title_de}"
        ): chapter.number
        for chapter in chapters
    }
    section_labels = {
        f"{section.id} {section.title}": (chapter.number, section)
        for chapter in chapters
        for section in chapter.sections
    }
    concept_labels = {
        f"📖 {card.front}": (chapter.number, card)
        for chapter in chapters
        for card in chapter.concepts
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

    def progress_label(ids: set[str], known: set[str]) -> str:
        if not ids:
            return "— no cards"
        return f"{round(100 * len(ids & known) / len(ids))}%"

    async def show_topics(message: Message, user_id: int) -> None:
        known = study.progress.known_item_ids(user_id)
        labels = []
        for label, number in topic_labels.items():
            chapter = curriculum.chapter(number)
            ids = {card.id for card in chapter.concepts} | {formula.id for formula in chapter.formulas} if chapter else set()
            labels.append(f"{label} · {progress_label(ids, known)}")
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(label)] for label in labels] + [[KeyboardButton(HOME)]],
            resize_keyboard=True, is_persistent=True,
        )
        await message.reply_text(
            "🗂 Themen auswählen\n\n1️⃣–🔟 Theorie · Eisert\n🔬 Experimentalphysik · Franke\n\nTippe unten auf ein Thema, um gezielt zu lernen.",
            reply_markup=keyboard,
        )

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
        cards = study.cards(chapter_number)
        if not cards:
            await message.reply_text("No learning cards are available for this topic yet.")
            await show_topics(message, int(context.user_data.get("viewer_id", 0)))
            return
        context.user_data["set_kind"] = "topic"
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
            chapter_number = selected_chapter(context)
            await message.reply_text(
                f"✅ Set complete · {len(session.cards)}/{len(session.cards)}\n"
                "100% completed in this set.\n"
                "This is recognition practice, not long-term or exam mastery.\n\n"
                "Choose another topic below."
            )
            context.user_data.pop("study_set", None)
            context.user_data.pop("question", None)
            context.user_data.pop("mode", None)
            await show_topics(message, int(context.user_data.get("viewer_id", 0)))
            return
        context.user_data["question"] = Question(
            card.id, "concept", card.front, f"{card.definition}\n\n{card.key_rule}"
        )
        distractors = list(dict.fromkeys(
            other.definition for other in study.cards()
            if other.definition != card.definition
        ))
        choices = random.sample(distractors, min(3, len(distractors))) + [card.definition]
        random.shuffle(choices)
        context.user_data["concept_choices"] = {
            f"{index + 1}️⃣ {definition}": definition == card.definition
            for index, definition in enumerate(choices)
        }
        context.user_data["mode"] = "concept_choice"
        context.user_data["presented_at"] = time.monotonic()
        await message.reply_text(
            f"📖 {session.position}/{len(session.cards)} · {session.percentage}% completed in this set\n\n"
            f"🧠 {card.front}\n\n❓ Which definition matches?",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(label)] for label in context.user_data["concept_choices"]]
                + [[KeyboardButton(DONT_KNOW)], [KeyboardButton(TOPICS), KeyboardButton(HOME)]],
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
        context.user_data["study_set"] = StudySet(cards)
        await message.reply_text(f"🔁 Review · {len(cards)} cards from all topics")
        await present_set_card(message, context)

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
            message, user = message_and_user(update)
            await show_topics(message, user.id)

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
        if context.user_data is not None:
            context.user_data["viewer_id"] = user.id
        # Old keyboard percentages may be stale after another answer; route by stable label.
        if " · " in text:
            base = text.rsplit(" · ", 1)[0]
            if base in topic_labels or base in section_labels:
                text = base
        if text in {HOME, TOPICS, LEARN, LAWS, FORMULAS} and context.user_data is not None:
            context.user_data.pop("study_set", None)
            context.user_data.pop("question", None)
            context.user_data.pop("mode", None)

        if text in {HOME, "/start"}:
            if context.user_data is not None:
                context.user_data.pop("selected_chapter", None)
            await send_menu(message)
        elif text in topic_labels:
            await select_topic(message, context, topic_labels[text])
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
        elif text in concept_labels:
            chapter_number, card = concept_labels[text]
            if context.user_data is None:
                return
            context.user_data["selected_chapter"] = chapter_number
            context.user_data["selected_section"] = card.section_id
            context.user_data["question"] = Question(
                card.id, "concept", card.front,
                f"{card.definition}\n\n{card.key_rule}",
            )
            context.user_data["mode"] = "concept"
            context.user_data["presented_at"] = time.monotonic()
            await message.reply_text(
                f"🧠 {card.front}\n\n❓ Explain the concept and its key rule.",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton(REVEAL)], [KeyboardButton(TOPICS), KeyboardButton(HOME)]],
                    resize_keyboard=True, is_persistent=True,
                ),
            )
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
            await show_topics(message, user.id)
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
                await send_menu(message, "This set expired. Choose a subsection again.")
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
        elif text == REVEAL:
            await reveal_flashcard(message, context)
        elif text in {KNOW, DONT_KNOW}:
            ratings: dict[str, ReviewRating] = {
                DONT_KNOW: "repeat", KNOW: "okay"
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
            [
                [KeyboardButton(KNOW), KeyboardButton(DONT_KNOW)],
                [KeyboardButton(HOME)],
            ],
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
        if context.user_data.get("mode") != "grading":
            await message.reply_text("Reveal the answer before rating your recall.")
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
        if question.item_type == "concept" and context.user_data.get("study_set") is not None:
            session: StudySet = context.user_data["study_set"]
            session.grade(rating)
            status = (
                "🔁 This card will return after the remaining cards."
                if rating in {"repeat", "hard"} and len(session.pending) > 1
                else "🔁 Try this card again." if rating in {"repeat", "hard"}
                else "✅ Card completed."
            )
            await message.reply_text(status)
            await present_set_card(message, context)
            return
        status = status_by_rating[rating]
        await message.reply_text(status)
        if question.item_type == "concept":
            await send_menu(message, "Choose another concept through Topics.")
            return
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
