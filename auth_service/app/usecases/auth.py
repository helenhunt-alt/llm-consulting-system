from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.users import UsersRepository


class AuthUseCase:
    def __init__(self, users_repository: UsersRepository) -> None:
        self.users_repository = users_repository

    async def register(self, email: str, password: str) -> User:
        existing_user = await self.users_repository.get_by_email(email)

        if existing_user is not None:
            raise UserAlreadyExistsError()

        password_hash = hash_password(password)

        return await self.users_repository.create(
            email=email,
            password_hash=password_hash,
            role="user",
        )

    async def login(self, email: str, password: str) -> str:
        user = await self.users_repository.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        return create_access_token(
            subject=user.id,
            role=user.role,
        )

    async def me(self, user_id: int) -> User:
        user = await self.users_repository.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError()

        return user
