from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings


def decode_and_validate(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_alg],
        )
    except ExpiredSignatureError as error:
        raise ValueError("Token has expired") from error
    except JWTError as error:
        raise ValueError("Invalid token") from error

    if payload.get("sub") is None:
        raise ValueError("Token payload does not contain sub")

    return payload
