import httpx
import pytest
import respx

from app.core.config import settings
from app.services.openrouter_client import (
    OpenRouterClientError,
    call_openrouter,
)


@pytest.mark.asyncio
async def test_call_openrouter_returns_answer() -> None:
    async with respx.mock(base_url=settings.openrouter_base_url) as router:
        route = router.post("/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "Mocked LLM answer",
                            }
                        }
                    ]
                },
            )
        )

        answer = await call_openrouter("Hello")

    assert route.called
    assert answer == "Mocked LLM answer"


@pytest.mark.asyncio
async def test_call_openrouter_handles_http_error() -> None:
    async with respx.mock(base_url=settings.openrouter_base_url) as router:
        router.post("/chat/completions").mock(
            return_value=httpx.Response(
                500,
                json={"error": "server error"},
            )
        )

        with pytest.raises(OpenRouterClientError):
            await call_openrouter("Hello")


@pytest.mark.asyncio
async def test_call_openrouter_handles_unexpected_response_format() -> None:
    async with respx.mock(base_url=settings.openrouter_base_url) as router:
        router.post("/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"unexpected": "format"},
            )
        )

        with pytest.raises(OpenRouterClientError):
            await call_openrouter("Hello")
