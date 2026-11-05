from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from telegram.ext import ContextTypes

from quantum_tutor.application.study import Question, StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository

MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📚 Terms", callback_data="menu:terms"),
        InlineKeyboardButton("🧮 Formulas", callback_data="menu:formulas"),
    ],
    [
        InlineKeyboardButton("🗂 Topics", callback_data="menu:topics"),
        InlineKeyboardButton("🔁 Review", callback_data="menu:review"),
    ],
    [InlineKeyboardButton("📈 Progress", callback_data="menu:progress")],
])


def build_handlers(
    study: StudyService,
    curriculum: CurriculumRepository,
    allowed_user_id: int,
):
    def message_and_user(update: Update) -> tuple[Message, User]:
        message, user = update.effective_message, update.effective_user
        if message is None or user is None:
            raise RuntimeError("Handler received an update without a message or user")
        return message, user

    async def reject_if_unauthorized(update: Update) -> bool:
        user = update.effective_user
        if user is not None and user.id == allowed_user_id:
            return False
        if update.callback_query is not None:
            await update.callback_query.answer("This is a private bot.", show_alert=True)
        elif update.effective_message is not None:
            await update.effective_message.reply_text("This is a private study bot.")
        return True

    async def send_menu(message: Message, text: str = "What would you like to study?") -> None:
        await message.reply_text(text, reply_markup=MAIN_MENU)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, _ = message_and_user(update)
        await send_menu(
            message,
            "👋 Welcome to Quantum Tutor. Use the buttons below for bilingual terms, formulas, review, and progress.",
        )

    async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, _ = message_and_user(update)
        lines = [f"{chapter.number}. {chapter.title_de} / {chapter.title}" for chapter in curriculum.chapters()]
        await message.reply_text("🗂 Course topics:\n" + "\n".join(lines), reply_markup=MAIN_MENU)

    async def ask(message: Message, context: ContextTypes.DEFAULT_TYPE, kind: str) -> None:
        question = study.random_term() if kind == "term" else study.random_formula()
        if question is None:
            await message.reply_text("No study material is available yet.", reply_markup=MAIN_MENU)
            return
        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        context.user_data["question"] = question
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("👀 Reveal answer", callback_data="question:reveal"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu:home"),
        ]])
        await message.reply_text(question.prompt, reply_markup=keyboard)

    async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await ask(message_and_user(update)[0], context, "term")

    async def formulas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await reject_if_unauthorized(update):
            await ask(message_and_user(update)[0], context, "formula")

    async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, user = message_and_user(update)
        await message.reply_text(
            f"🔁 You have {study.due_count(user.id)} item(s) due for review.",
            reply_markup=MAIN_MENU,
        )

    async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        message, user = message_and_user(update)
        await message.reply_text("📈 Your progress\n\n" + study.progress_text(user.id), reply_markup=MAIN_MENU)

    async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await reject_if_unauthorized(update):
            return
        query = update.callback_query
        if query is None or query.message is None:
            return
        await query.answer()
        data = query.data or ""

        if data.startswith("menu:"):
            action = data.removeprefix("menu:")
            if action == "terms":
                await ask(query.message, context, "term")
            elif action == "formulas":
                await ask(query.message, context, "formula")
            elif action == "topics":
                lines = [f"{c.number}. {c.title_de} / {c.title}" for c in curriculum.chapters()]
                await query.message.reply_text("🗂 Course topics:\n" + "\n".join(lines), reply_markup=MAIN_MENU)
            elif action == "review":
                await query.message.reply_text(
                    f"🔁 You have {study.due_count(query.from_user.id)} item(s) due.", reply_markup=MAIN_MENU
                )
            elif action == "progress":
                await query.message.reply_text(
                    "📈 Your progress\n\n" + study.progress_text(query.from_user.id), reply_markup=MAIN_MENU
                )
            else:
                await send_menu(query.message)
            return

        if context.user_data is None:
            raise RuntimeError("Per-user storage is unavailable")
        question: Question | None = context.user_data.get("question")
        if question is None:
            await query.message.reply_text("This question expired. Choose a new one.", reply_markup=MAIN_MENU)
            return
        if data == "question:reveal":
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ I knew it", callback_data="grade:1"),
                    InlineKeyboardButton("🔁 Review again", callback_data="grade:0"),
                ],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu:home")],
            ])
            await query.edit_message_text(f"{question.prompt}\n\n{question.answer}", reply_markup=keyboard)
        elif data.startswith("grade:"):
            correct = data == "grade:1"
            study.record(query.from_user.id, question, correct)
            context.user_data.pop("question", None)
            await query.edit_message_text("Saved ✅")
            await send_menu(query.message, "Choose your next activity:")

    return start, topics, terms, formulas, review, progress, callback
