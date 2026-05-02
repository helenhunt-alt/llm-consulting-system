from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.core.jwt import decode_and_validate
from app.infra.redis import get_redis
from app.tasks.llm_tasks import llm_request

router = Router()

TOKEN_TTL_SECONDS = 24 * 60 * 60


def build_token_key(telegram_user_id: int) -> str:
    return f"token:{telegram_user_id}"


def get_telegram_user_id(message: Message) -> int | None:
    if message.from_user is None:
        return None

    return message.from_user.id


@router.message(Command("start"))
async def handle_start_command(message: Message) -> None:
    await message.answer(
        "Привет! Чтобы пользоваться LLM-консультациями, "
        "сначала получите JWT в Auth Service и отправьте его командой:\n\n"
        "/token <JWT>"
    )


@router.message(Command("token"))
async def handle_token_command(
    message: Message,
    command: CommandObject,
) -> None:
    telegram_user_id = get_telegram_user_id(message)

    if telegram_user_id is None:
        await message.answer("Не удалось определить Telegram user_id.")
        return

    if command.args is None or not command.args.strip():
        await message.answer("Передайте токен в формате: /token <JWT>")
        return

    token = command.args.strip()

    try:
        decode_and_validate(token)
    except ValueError:
        await message.answer(
            "Токен недействителен или истёк. "
            "Получите новый токен в Auth Service."
        )
        return

    redis_client = get_redis()
    await redis_client.set(
        build_token_key(telegram_user_id),
        token,
        ex=TOKEN_TTL_SECONDS,
    )

    await message.answer("Токен принят и сохранён.")


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    telegram_user_id = get_telegram_user_id(message)

    if telegram_user_id is None:
        await message.answer("Не удалось определить Telegram user_id.")
        return

    if message.text is None:
        return

    if message.text.startswith("/"):
        await message.answer("Неизвестная команда.")
        return

    redis_client = get_redis()
    token_key = build_token_key(telegram_user_id)
    token = await redis_client.get(token_key)

    if token is None:
        await message.answer(
            "Доступ закрыт. Сначала отправьте JWT командой:\n\n"
            "/token <JWT>"
        )
        return

    try:
        decode_and_validate(token)
    except ValueError:
        await redis_client.delete(token_key)
        await message.answer(
            "Сохранённый токен недействителен или истёк. "
            "Получите новый токен в Auth Service."
        )
        return

    llm_request.delay(
        message.chat.id,
        message.text,
    )

    await message.answer(
        "Запрос принят. Ответ придёт следующим сообщением."
    )
