from __future__ import annotations


import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from aiohttp import web

from quantum_tutor.application.study import Exercise, StudyService
from quantum_tutor.config import Settings
from quantum_tutor.domain.study_set import StudySet
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.web.auth import AuthenticationError, authenticate_init_data
from quantum_tutor.web.math_rendering import answer_latex, blocks, literal_latex

STATIC = Path(__file__).parent / "static"


def latex_for_choice(text: str) -> str:
    return literal_latex(text)


@dataclass
class Session:
    title: str
    mode: str
    study_set: StudySet | None
    question_id: str = ""
    exercise: Exercise | None = None
    started: float = field(default_factory=time.monotonic)
    touched: float = field(default_factory=time.monotonic)


def create_web_app(settings: Settings) -> web.Application:
    curriculum = CurriculumRepository(settings.curriculum_path)
    study = StudyService(curriculum, ProgressRepository(settings.database_path))
    sessions: dict[int, Session] = {}
    requests: dict[int, list[float]] = {}

    @web.middleware
    async def security(request: web.Request, handler):
        try:
            if request.path.startswith("/api/"):
                authorization = request.headers.get("Authorization", "")
                if not authorization:
                    raise AuthenticationError("Open this app from Telegram.", "auth_missing")
                scheme, separator, init_data = authorization.partition(" ")
                if scheme.lower() != "tma":
                    raise AuthenticationError("Invalid Telegram authorization header.")
                if not separator or not init_data:
                    raise AuthenticationError("Telegram sign-in data is missing.", "auth_missing")
                user_id = authenticate_init_data(
                    init_data, settings.telegram_token, settings.allowed_user_ids,
                    public_access=settings.public_access,
                )
                request["user_id"] = user_id
                now = time.monotonic()
                recent = [stamp for stamp in requests.get(user_id, []) if now - stamp < 60]
                if len(recent) >= 120:
                    return web.json_response({"error": "Too many requests. Try again shortly."}, status=429)
                requests[user_id] = recent + [now]
            response = await handler(request)
        except AuthenticationError as error:
            response = web.json_response({"error": str(error), "code": error.code}, status=401)
        except PermissionError as error:
            response = web.json_response({"error": str(error), "code": "auth_forbidden"}, status=403)
        except (json.JSONDecodeError, ValueError, TypeError):
            response = web.json_response({"error": "Invalid request data."}, status=400)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app = web.Application(middlewares=[security], client_max_size=32768)

    catalog = {card.id: card for card in study.cards()}
    source_notes = {card_id: note for chapter in curriculum.chapters()
                    for card_id, note in chapter.content_review_required.items()}

    def choice_payload(exercise: Exercise, index: int, formula: bool) -> dict:
        text = exercise.choices[index]
        source_id = exercise.choice_card_ids[index] if exercise.choice_card_ids else ""
        card = catalog.get(source_id)
        # Identity alone is insufficient: the selected excerpt must also match.
        paired = card if card and study.formula_text(card) == text else None
        latex = answer_latex(text, paired) if formula else ""
        return {"text": text, "latex": latex,
                "blocks": [{"type": "math" if latex else "text", "text": text, "latex": latex}]}


    def prepare(session: Session) -> None:
        card = session.study_set.current if session.study_set else None
        if card is not None:
            session.exercise = study.set_exercise(card, session.mode)
            session.question_id = secrets.token_urlsafe(18)
            session.started = time.monotonic()
        else:
            session.exercise = None
            session.question_id = ""

    def state(session: Session) -> dict:
        queue = session.study_set
        exercise = session.exercise
        complete = queue is None or queue.current is None
        question = None
        if exercise is not None and not complete:
            formula = study.has_formula(queue.current)
            question = {
                "id": session.question_id,
                "card_id": exercise.question.item_id,
                "prompt": exercise.question.prompt,
                "prompt_blocks": blocks(exercise.question.prompt),
                "choices": [choice_payload(exercise, index, formula)
                            for index in range(len(exercise.choices))],
            }
        return {
            "complete": complete,
            "title": session.title,
            "total": len(queue.cards) if queue else 0,
            "completed": len(queue.mastered) if queue else 0,
            "percent": queue.percentage if queue else 100,
            "position": queue.position if queue else 0,
            "question": question,
        }

    def current(user_id: int) -> Session | None:
        session = sessions.get(user_id)
        if session is not None and time.monotonic() - session.touched > 7200:
            sessions.pop(user_id, None)
            return None
        if session is not None:
            session.touched = time.monotonic()
        return session

    async def topics(request):
        mode = request.query.get("mode", "learn")
        if mode not in {"learn", "formula", "law"}:
            raise ValueError("Invalid mode")
        known = study.progress.known_item_ids(request["user_id"])
        review_ids = {card.id for card in study.review_cards(request["user_id"])}
        items = []
        for chapter in curriculum.chapters():
            cards = study.mode_cards(chapter.number, mode)
            ids = {card.id for card in cards}
            items.append({
                "number": chapter.number,
                "title": chapter.title,
                "title_de": chapter.title_de,
                "professor": chapter.professor,
                "date": chapter.date,
                "card_count": len(cards),
                "review_count": len(ids & review_ids),
                "percent": round(100 * len(ids & known) / len(ids)) if ids else 0,
            })
        return web.json_response({"topics": items, "review_count": study.due_count(request["user_id"])})

    async def progress(request):
        user_id = request["user_id"]
        total, correct = study.progress.statistics(user_id)
        known = study.progress.known_item_ids(user_id)
        ids = {card.id for card in study.cards()}
        return web.json_response({
            "answered": total, "correct": correct,
            "accuracy": round(100 * correct / total) if total else 0,
            "review_count": study.due_count(user_id), "known": len(ids & known), "total": len(ids),
        })

    async def begin(request):
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Expected object")
        mode = body.get("mode", "learn")
        if mode not in {"learn", "formula", "law"}:
            raise ValueError("Invalid mode")
        review = body.get("review", False)
        if type(review) is not bool:
            raise ValueError("Invalid review flag")
        if review:
            cards = study.review_cards(request["user_id"])
            topic_id = body.get("topic_id")
            if topic_id is not None:
                if type(topic_id) is not int or curriculum.chapter(topic_id) is None:
                    raise ValueError("Invalid review topic")
                eligible = {card.id for card in study.mode_cards(topic_id, mode)}
                cards = tuple(card for card in cards if card.id in eligible)
            elif mode == "formula":
                cards = tuple(card for card in cards if study.has_formula(card))
            title = "Review" if topic_id is None else f"Review · {curriculum.chapter(topic_id).title_de}"
        else:
            topic_id = body.get("topic_id")
            if topic_id is None:
                cards = tuple(card for chapter in curriculum.chapters() for card in study.mode_cards(chapter.number, mode))
                title = "All chapters & experiments"
            else:
                if type(topic_id) is not int:
                    raise ValueError("Invalid topic")
                chapter = curriculum.chapter(topic_id)
                if chapter is None:
                    raise web.HTTPNotFound(text="Unknown topic")
                cards = study.mode_cards(topic_id, mode)
                title = chapter.title_de
        session = Session(title, mode, StudySet(cards) if cards else None)
        prepare(session)
        sessions[request["user_id"]] = session
        return web.json_response(state(session))

    async def get_session(request):
        session = current(request["user_id"])
        if session is None:
            return web.json_response({"error": "No active session."}, status=404)
        return web.json_response(state(session))

    async def answer(request):
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Expected object")
        session = current(request["user_id"])
        if session is None or session.exercise is None:
            return web.json_response({"error": "Session expired. Start another set."}, status=409)
        if body.get("question_id") != session.question_id:
            return web.json_response({"error": "This question has already changed. Resume the set."}, status=409)
        if "choice_index" not in body:
            raise ValueError("An answer choice is required")
        choice = body["choice_index"]
        if choice is not None and (type(choice) is not int or not 0 <= choice < len(session.exercise.choices)):
            raise ValueError("Invalid answer choice")
        exercise = session.exercise
        correct = choice is not None and choice == exercise.correct_index
        note = source_notes.get(exercise.question.item_id, "")
        card = catalog.get(exercise.question.item_id)
        latex = answer_latex(exercise.question.answer, card) if card and study.has_formula(card) else ""
        # No await between validating the nonce and replacing it: duplicate submissions
        # cannot record the same question twice in this single-event-loop service.
        study.record(
            request["user_id"], exercise.question, correct,
            rating="okay" if correct else "repeat",
            response_ms=max(0, round((time.monotonic() - session.started) * 1000)),
        )
        session.study_set.grade("okay" if correct else "repeat")
        answer_blocks = blocks(exercise.question.answer)
        if card and exercise.question.answer == card.formula_answer and card.formula_answer_latex:
            answer_blocks = [{"type": "math", "text": exercise.question.answer, "latex": latex}]
        feedback = {"correct": correct, "answer": exercise.question.answer, "latex": latex,
                    "answer_blocks": answer_blocks, "source_note": note}
        prepare(session)
        return web.json_response({"feedback": feedback, "state": state(session)})

    async def end(request):
        sessions.pop(request["user_id"], None)
        return web.json_response({"ok": True})

    async def health(request):
        return web.json_response({"ok": True})

    async def static_file(request):
        name = request.match_info.get("name", "index.html")
        if name not in {"index.html", "app.js", "styles.css", "crystal.js", "inertia.js", "mini-crystals.js", "crystal-audio.js", "crystal-crumple.mp3", "metal-ball-audio.js"}:
            raise web.HTTPNotFound()
        response = web.FileResponse(STATIC / name)
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://telegram.org https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; connect-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'none'"
        )
        return response

    app.router.add_get("/healthz", health)
    app.router.add_get("/api/topics", topics)
    app.router.add_get("/api/progress", progress)
    app.router.add_post("/api/session", begin)
    app.router.add_get("/api/session", get_session)
    app.router.add_post("/api/session/end", end)
    app.router.add_post("/api/answer", answer)
    app.router.add_get("/", static_file)
    app.router.add_get("/{name}", static_file)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Never log initData, Authorization headers, or bot tokens.
    web.run_app(create_web_app(Settings.from_env()), host="0.0.0.0", port=8080, access_log=None)


if __name__ == "__main__":
    main()
