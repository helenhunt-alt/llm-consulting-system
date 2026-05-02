from typing import Any

import httpx

from app.core.config import settings


class OpenRouterClientError(Exception):
    pass


class OpenRouterClient:
    def __init__(
        self,
        base_url: str = settings.openrouter_base_url,
        api_key: str = settings.openrouter_api_key,
        model: str = settings.openrouter_model,
        site_url: str = settings.openrouter_site_url,
        app_name: str = settings.openrouter_app_name,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout

    async def get_chat_completion(self, prompt: str) -> str:
        payload = self._build_payload(prompt)
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            raise OpenRouterClientError(
                f"OpenRouter returned HTTP {status_code}"
            ) from error
        except httpx.RequestError as error:
            raise OpenRouterClientError("OpenRouter request failed") from error

        return self._extract_answer(response.json())

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }

    def _extract_answer(self, data: dict[str, Any]) -> str:
        try:
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OpenRouterClientError(
                "Unexpected OpenRouter response format"
            ) from error

        if not isinstance(answer, str) or not answer.strip():
            raise OpenRouterClientError("OpenRouter returned empty answer")

        return answer


async def call_openrouter(prompt: str) -> str:
    client = OpenRouterClient()
    return await client.get_chat_completion(prompt)
