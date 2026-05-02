import asyncio

from aiogram import Bot

from app.core.config import settings
from app.infra.celery_app import celery_app
from app.services.openrouter_client import OpenRouterClientError, call_openrouter


async def send_answer_to_telegram(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(token=settings.telegram_bot_token)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
        )
    finally:
        await bot.session.close()


@celery_app.task(name="app.tasks.llm_tasks.llm_request")
def llm_request(tg_chat_id: int, prompt: str) -> dict[str, int | str]:
    try:
        answer = asyncio.run(call_openrouter(prompt))
    except OpenRouterClientError:
        answer = "Не удалось получить ответ от LLM. Попробуйте позже."

    asyncio.run(
        send_answer_to_telegram(
            chat_id=tg_chat_id,
            text=answer,
        )
    )

    return {
        "status": "sent",
        "chat_id": tg_chat_id,
    }
