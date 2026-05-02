import pytest

from app.services.openrouter_client import OpenRouterClientError
from app.tasks import llm_tasks


@pytest.fixture(autouse=True)
def restore_task_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_tasks, "call_openrouter", llm_tasks.call_openrouter)
    monkeypatch.setattr(
        llm_tasks,
        "send_answer_to_telegram",
        llm_tasks.send_answer_to_telegram,
    )


def test_llm_request_sends_llm_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_messages: list[tuple[int, str]] = []

    async def fake_call_openrouter(prompt: str) -> str:
        return f"Mocked LLM answer for: {prompt}"

    async def fake_send_answer_to_telegram(chat_id: int, text: str) -> None:
        sent_messages.append((chat_id, text))

    monkeypatch.setattr(llm_tasks, "call_openrouter", fake_call_openrouter)
    monkeypatch.setattr(
        llm_tasks,
        "send_answer_to_telegram",
        fake_send_answer_to_telegram,
    )

    result = llm_tasks.llm_request.run(
        tg_chat_id=12345,
        prompt="Расскажи кратко про FastAPI",
    )

    assert result == {
        "status": "sent",
        "chat_id": 12345,
    }
    assert sent_messages == [
        (
            12345,
            "Mocked LLM answer for: Расскажи кратко про FastAPI",
        )
    ]


def test_llm_request_sends_fallback_on_openrouter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_messages: list[tuple[int, str]] = []

    async def fake_call_openrouter(prompt: str) -> str:
        raise OpenRouterClientError("test error")

    async def fake_send_answer_to_telegram(chat_id: int, text: str) -> None:
        sent_messages.append((chat_id, text))

    monkeypatch.setattr(llm_tasks, "call_openrouter", fake_call_openrouter)
    monkeypatch.setattr(
        llm_tasks,
        "send_answer_to_telegram",
        fake_send_answer_to_telegram,
    )

    result = llm_tasks.llm_request.run(
        tg_chat_id=12345,
        prompt="Расскажи кратко про FastAPI",
    )

    assert result == {
        "status": "sent",
        "chat_id": 12345,
    }
    assert sent_messages == [
        (
            12345,
            "Не удалось получить ответ от LLM. Попробуйте позже.",
        )
    ]
