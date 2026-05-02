from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_session
from app.repositories.users import UsersRepository
from app.usecases.auth import AuthUseCase

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def get_users_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UsersRepository:
    return UsersRepository(session)


def get_auth_uc(
    users_repository: Annotated[UsersRepository, Depends(get_users_repo)],
) -> AuthUseCase:
    return AuthUseCase(users_repository)


def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    try:
        payload = decode_token(token)
    except ExpiredSignatureError as error:
        raise TokenExpiredError() from error
    except JWTError as error:
        raise InvalidTokenError() from error

    user_id = payload.get("sub")

    if user_id is None:
        raise InvalidTokenError()

    try:
        return int(user_id)
    except ValueError as error:
        raise InvalidTokenError() from error


async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    auth_use_case: Annotated[AuthUseCase, Depends(get_auth_uc)],
) -> User:
    return await auth_use_case.me(user_id)
