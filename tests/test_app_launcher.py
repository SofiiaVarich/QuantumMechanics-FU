import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quantum_tutor.application.study import StudyService
from quantum_tutor.infrastructure.curriculum import CurriculumRepository
from quantum_tutor.presentation.handlers import OPEN_APP, build_handlers, main_keyboard


def test_keyboard_and_command_share_authenticated_inline_launcher():
    url = "https://example.test/"
    button = main_keyboard(url).keyboard[0][0]
    assert button.text == OPEN_APP
    assert button.web_app is None
    repository = CurriculumRepository(Path("curriculum"))
    handlers = build_handlers(StudyService(repository, None), repository, (123,), url)
    outputs = []
    for text, handler in ((OPEN_APP, handlers[-1]), ("/app", handlers[0])):
        message = SimpleNamespace(text=text, reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=123),
                                 effective_chat=SimpleNamespace(type="private"))
        context = SimpleNamespace(user_data={"selected_chapter": 3})
        asyncio.run(handler(update, context))
        assert context.user_data == {"selected_chapter": 3}
        markup = message.reply_text.call_args.kwargs["reply_markup"]
        assert markup.inline_keyboard[0][0].web_app.url == url
        outputs.append(markup.to_dict())
    assert outputs[0] == outputs[1]
