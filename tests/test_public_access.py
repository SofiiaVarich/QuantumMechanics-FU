import asyncio
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from quantum_tutor.config import Settings
from quantum_tutor.main import create_application
from quantum_tutor.presentation.handlers import build_handlers
from quantum_tutor.web.auth import AuthenticationError, authenticate_init_data
from quantum_tutor.web.server import create_web_app
from test_web_auth import TOKEN, signed_data


def settings(tmp_path, ids=(), public=True):
    return Settings(TOKEN, tmp_path / "db.sqlite", Path("curriculum"), ids,
                    "Europe/Berlin", "20:00", public_access=public)


@pytest.mark.parametrize("public", [False, True])
def test_auth_policy(public):
    if public:
        assert authenticate_init_data(signed_data(789), TOKEN, (), public_access=True, now=1001) == 789
    else:
        with pytest.raises(PermissionError):
            authenticate_init_data(signed_data(789), TOKEN, (), now=1001)
    for value in (signed_data(0), signed_data(-1), signed_data(True), signed_data("123"),
                  signed_data() + "&auth_date=1000", signed_data().replace("1000", "1001"),
                  signed_data(timestamp=1), signed_data(timestamp=5000)):
        with pytest.raises(AuthenticationError):
            authenticate_init_data(value, TOKEN, (123,), public_access=public, now=4000)


@pytest.mark.parametrize("value,expected", [(None, False), ("false", False), ("true", True), (" TRUE ", True)])
def test_config_boolean(monkeypatch, value, expected):
    monkeypatch.setattr("quantum_tutor.config.load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123")
    monkeypatch.delenv("PUBLIC_ACCESS", raising=False)
    if value is not None:
        monkeypatch.setenv("PUBLIC_ACCESS", value)
    assert Settings.from_env().public_access is expected


@pytest.mark.parametrize("value", ["", "tru", "1", "yes"])
def test_config_rejects_boolean_typos(monkeypatch, value):
    monkeypatch.setattr("quantum_tutor.config.load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("PUBLIC_ACCESS", value)
    with pytest.raises(RuntimeError, match="PUBLIC_ACCESS"):
        Settings.from_env()


def test_config_empty_allowlist(monkeypatch):
    monkeypatch.setattr("quantum_tutor.config.load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    for name in ("TELEGRAM_ALLOWED_USER_IDS", "TELEGRAM_ALLOWED_USER_ID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PUBLIC_ACCESS", "false")
    with pytest.raises(RuntimeError):
        Settings.from_env()
    monkeypatch.setenv("PUBLIC_ACCESS", "true")
    assert Settings.from_env().allowed_user_ids == ()
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "-123")
    with pytest.raises(RuntimeError, match="positive"):
        Settings.from_env()


@pytest.mark.parametrize("public,ids,user_id,chat_type,allowed", [
    (False, (), 789, "private", False),
    (False, (123,), 789, "private", False),
    (False, (123,), 123, "private", True),
    (True, (), 789, "private", True),
    (True, (123,), 789, "private", True),
    (True, (), None, "private", False),
    (True, (), 0, "private", False),
    (True, (), 789, "group", False),
    (False, (123,), 123, "supergroup", False),
])
def test_bot_access(tmp_path, public, ids, user_id, chat_type, allowed):
    from quantum_tutor.application.study import StudyService
    from quantum_tutor.infrastructure.curriculum import CurriculumRepository
    from quantum_tutor.infrastructure.database import ProgressRepository

    curriculum = CurriculumRepository(Path("curriculum"))
    study = StudyService(curriculum, ProgressRepository(tmp_path / "bot.sqlite"))
    handlers = build_handlers(study, curriculum, ids, public_access=public)
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message,
                             effective_user=SimpleNamespace(id=user_id) if user_id is not None else None,
                             effective_chat=SimpleNamespace(type=chat_type))
    context = SimpleNamespace(user_data={})
    asyncio.run(handlers[0](update, context))
    assert (context.user_data.get("viewer_id") == user_id and user_id is not None) is allowed
    assert ("Welcome" in message.reply_text.call_args.args[0]) is allowed


@pytest.mark.parametrize("ids", [(), (123,)])
def test_reminders_only_configured_recipients(tmp_path, ids):
    with patch("quantum_tutor.main.schedule_reminders") as schedule:
        create_application(settings(tmp_path, ids))
    assert [call.args[1] for call in schedule.call_args_list] == list(ids)


def test_public_api_auth_replay_and_account_isolation(tmp_path):
    async def scenario():
        async with TestClient(TestServer(create_web_app(settings(tmp_path)))) as client:
            now = int(time.time())
            headers = {"Authorization": "tma " + signed_data(789, now)}
            other = {"Authorization": "tma " + signed_data(987, now)}
            assert (await client.get("/api/topics")).status == 401
            for value in (signed_data(789, now - 3601), signed_data(789, now + 100),
                          signed_data(789, now) + "&auth_date=1", signed_data(0, now),
                          signed_data(789, now).replace("hash=", "hash=bad")):
                assert (await client.get("/api/topics", headers={"Authorization": "tma " + value})).status == 401
            assert (await client.get("/api/topics", headers=headers)).status == 200
            state = await (await client.post("/api/session", headers=headers,
                                            json={"mode": "formula", "topic_id": 3})).json()
            question_id = state["question"]["id"]
            body = {"question_id": question_id, "choice_index": None, "user_id": 789}
            assert (await client.get("/api/session", headers=other)).status == 404
            assert (await client.post("/api/answer", headers=other, json=body)).status == 409
            await client.post("/api/session", headers=other, json={"topic_id": 3})
            assert (await client.post("/api/answer", headers=other, json=body)).status == 409
            assert (await client.post("/api/answer", headers=headers, json=body)).status == 200
            assert (await client.post("/api/answer", headers=headers, json=body)).status == 409
            assert (await (await client.get("/api/progress", headers=headers)).json())["answered"] == 1
            assert (await (await client.get("/api/progress?user_id=789", headers=other)).json())["answered"] == 0
            await client.post("/api/session/end", headers=other, json={"user_id": 789})
            assert (await client.get("/api/session", headers=headers)).status == 200
    asyncio.run(scenario())
