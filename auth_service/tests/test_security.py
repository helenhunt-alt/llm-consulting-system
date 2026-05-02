from datetime import timedelta

import pytest
from jose import ExpiredSignatureError

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plain_password() -> None:
    password = "strong-password"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)


def test_verify_password_rejects_wrong_password() -> None:
    password = "strong-password"
    password_hash = hash_password(password)

    assert not verify_password("wrong-password", password_hash)


def test_create_access_token_contains_required_fields() -> None:
    token = create_access_token(subject=1, role="user")

    payload = decode_token(token)

    assert payload["sub"] == "1"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_token_rejects_expired_token() -> None:
    token = create_access_token(
        subject=1,
        role="user",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(ExpiredSignatureError):
        decode_token(token)
