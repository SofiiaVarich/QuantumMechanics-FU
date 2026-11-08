import asyncio
import time
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from quantum_tutor.config import Settings
from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.infrastructure.database import ProgressRepository
from quantum_tutor.web.server import create_web_app
from test_web_auth import TOKEN, signed_data


def test_web_app_auth_grading_replay_and_shared_progress(tmp_path: Path) -> None:
    settings = Settings(TOKEN, tmp_path / "db.sqlite", Path("curriculum"), (123, 456), "Europe/Berlin", "20:00")

    async def scenario():
        async with TestClient(TestServer(create_web_app(settings))) as client:
            response = await client.get("/")
            assert response.status == 200
            assert "Telegram" in await response.text()
            assert (await client.get("/.env")).status == 404
            assert (await client.get("/api/topics")).status == 401
            assert (await client.get("/api/topics", headers={"Authorization": "tma " + signed_data(789, int(time.time()))})).status == 403
            headers = {"Authorization": "tma " + signed_data(123, int(time.time()))}
            other = {"Authorization": "tma " + signed_data(456, int(time.time()))}
            response = await client.get("/api/topics?mode=formula", headers=headers)
            data = await response.json()
            assert len(data["topics"]) == 20
            assert data["topics"][2]["card_count"] > 1
            assert response.headers["Cache-Control"] == "no-store"
            response = await client.post("/api/session", headers=headers, json={"mode": "formula", "topic_id": 3})
            state = await response.json()
            assert state["total"] > 1
            question = state["question"]
            assert "correct_index" not in question
            assert "answer" not in question
            assert len(question["choices"]) >= 2
            assert (await client.get("/api/session", headers=other)).status == 404
            response = await client.post("/api/answer", headers=headers, json={"question_id": question["id"], "choice_index": None})
            result = await response.json()
            assert result["feedback"]["correct"] is False
            assert result["state"]["completed"] == 0
            assert result["state"]["question"]["card_id"] != question["card_id"]
            assert (await client.post("/api/answer", headers=headers, json={"question_id": question["id"], "choice_index": None})).status == 409
            progress = await (await client.get("/api/progress", headers=headers)).json()
            assert progress["answered"] == 1
            assert progress["review_count"] == 1
            assert (await (await client.get("/api/progress", headers=other)).json())["answered"] == 0
            review = await (await client.post("/api/session", headers=headers, json={"review": True, "mode": "learn"})).json()
            assert review["total"] == 1
            assert review["question"]["card_id"] == question["card_id"]
            # Find the correct answer through the trusted service, not a leaked API field.
            study = StudyService(CurriculumRepository(Path("curriculum")), ProgressRepository(settings.database_path))
            card = next(card for card in study.cards() if card.id == question["card_id"])
            correct_text = study.formula_text(card) if study.has_formula(card) else card.definition
            index = next(i for i, choice in enumerate(review["question"]["choices"]) if choice["text"] == correct_text)
            result = await (await client.post("/api/answer", headers=headers, json={"question_id": review["question"]["id"], "choice_index": index})).json()
            assert result["feedback"]["correct"] is True
            assert result["state"]["complete"] is True
            assert result["state"]["percent"] == 100
            assert study.review_cards(123) == ()
            assert (await client.post("/api/session/end", headers=headers, json={})).status == 200
            assert (await client.get("/api/session", headers=headers)).status == 404
            assert (await client.post("/api/session", headers=headers, json={"mode": "invalid"})).status == 400
    asyncio.run(scenario())
