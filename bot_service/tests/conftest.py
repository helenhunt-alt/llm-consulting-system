from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest_asyncio

import app.bot.handlers as handlers


@pytest_asyncio.fixture
async def handlers_fake_redis() -> AsyncGenerator[
    fakeredis.aioredis.FakeRedis,
    None,
]:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    handlers.get_redis = lambda: redis_client

    try:
        yield redis_client
    finally:
        await redis_client.aclose()
