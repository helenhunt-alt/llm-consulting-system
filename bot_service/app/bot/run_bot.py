import asyncio

from app.bot.dispatcher import create_bot, create_dispatcher


async def main() -> None:
    bot = create_bot()
    dispatcher = create_dispatcher()

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
