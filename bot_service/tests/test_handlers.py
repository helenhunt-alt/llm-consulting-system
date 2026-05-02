from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from aiogram.filters.command import CommandObject
from jose import jwt

import app.bot.handlers as handlers
from app.core.config import settings


class FakeUser:
    id = 12345


class FakeChat:
    id = 67890


class FakeDelay:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def __call__(self, chat_id: int, prompt: str) -> None:
        self.calls.append((chat_id, prompt))


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.from_user = FakeUser()
        self.chat = FakeChat()
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


def create_test_token() -> str:
    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": "1",
            "role": "user",
            "iat": int(now.timestamp()),
            "exp": now + timedelta(minutes=10),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )


@pytest.mark.asyncio
async def test_token_command_saves_valid_token(
    handlers_fake_redis: Any,
) -> None:
    token = create_test_token()
    message = FakeMessage(f"/token {token}")
    command = CommandObject(
        prefix="/",
        command="token",
        mention=None,
        args=token,
    )

    await handlers.handle_token_command(message, command)

    saved_token = await handlers_fake_redis.get(
        handlers.build_token_key(FakeUser.id)
    )

    assert saved_token == token
    assert message.answers[-1] == "Токен принят и сохранён."


@pytest.mark.asyncio
async def test_token_command_rejects_invalid_token(
    handlers_fake_redis: Any,
) -> None:
    message = FakeMessage("/token invalid-token")
    command = CommandObject(
        prefix="/",
        command="token",
        mention=None,
        args="invalid-token",
    )

    await handlers.handle_token_command(message, command)

    saved_token = await handlers_fake_redis.get(
        handlers.build_token_key(FakeUser.id)
    )

    assert saved_token is None
    assert message.answers[-1] == (
        "Токен недействителен или истёк. "
        "Получите новый токен в Auth Service."
    )


@pytest.mark.asyncio
async def test_text_message_without_token_does_not_enqueue_task(
    handlers_fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_delay = FakeDelay()

    monkeypatch.setattr(handlers.llm_request, "delay", fake_delay)

    message = FakeMessage("Расскажи кратко про FastAPI")

    await handlers.handle_text_message(message)

    assert fake_delay.calls == []
    assert message.answers[-1] == (
        "Доступ закрыт. Сначала отправьте JWT командой:\n\n"
        "/token <JWT>"
    )


@pytest.mark.asyncio
async def test_text_message_with_valid_token_enqueues_task(
    handlers_fake_redis: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_delay = FakeDelay()

    monkeypatch.setattr(handlers.llm_request, "delay", fake_delay)

    token = create_test_token()
    await handlers_fake_redis.set(
        handlers.build_token_key(FakeUser.id),
        token,
    )

    message = FakeMessage("Расскажи кратко про FastAPI")

    await handlers.handle_text_message(message)

    assert fake_delay.calls == [
        (FakeChat.id, "Расскажи кратко про FastAPI")
    ]
    assert message.answers[-1] == (
        "Запрос принят. Ответ придёт следующим сообщением."
    )
