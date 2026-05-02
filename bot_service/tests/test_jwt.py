from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.jwt import decode_and_validate


def create_test_token(
    subject: str = "123",
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire_at = now + (expires_delta or timedelta(minutes=10))

    return jwt.encode(
        {
            "sub": subject,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": expire_at,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )


def test_decode_and_validate_returns_payload_for_valid_token() -> None:
    token = create_test_token(subject="123", role="user")

    payload = decode_and_validate(token)

    assert payload["sub"] == "123"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_and_validate_rejects_invalid_token() -> None:
    with pytest.raises(ValueError):
        decode_and_validate("invalid-token")


def test_decode_and_validate_rejects_expired_token() -> None:
    token = create_test_token(
        subject="123",
        role="user",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ValueError):
        decode_and_validate(token)


def test_decode_and_validate_rejects_token_without_subject() -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "role": "user",
            "iat": int(now.timestamp()),
            "exp": now + timedelta(minutes=10),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )

    with pytest.raises(ValueError):
        decode_and_validate(token)
