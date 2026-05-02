from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()


def make_email() -> str:
    return f"user-{uuid4().hex[:8]}@email.com"


@pytest.mark.asyncio
async def test_register_login_and_get_me(client: AsyncClient) -> None:
    email = make_email()
    password = "strong-password"

    register_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    registered_user = register_response.json()

    assert registered_user["email"] == email
    assert registered_user["role"] == "user"
    assert "id" in registered_user
    assert "created_at" in registered_user
    assert "password_hash" not in registered_user

    login_response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )

    assert me_response.status_code == 200

    current_user = me_response.json()

    assert current_user["email"] == email
    assert current_user["role"] == "user"
    assert "password_hash" not in current_user


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(
    client: AsyncClient,
) -> None:
    email = make_email()
    password = "strong-password"

    first_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )
    second_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "User with this email already exists"
    )


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: AsyncClient,
) -> None:
    email = make_email()

    await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password",
        },
    )

    login_response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "wrong-password",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_get_me_without_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_invalid_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"
