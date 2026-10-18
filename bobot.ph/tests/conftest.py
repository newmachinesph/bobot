import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings
from api.main import app
from packages.db.base import Base
from packages.db.engine import get_db


def _make_engine():
    return create_async_engine(
        settings.async_database_url,
        echo=False,
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,
        connect_args={"ssl": True},
    )


_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = _make_engine()
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine, _session_factory


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_engine()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def _ensure_tables():
    """Create tables if they don't exist."""
    global _engine, _session_factory
    # Recreate engine on current event loop
    _engine = _make_engine()
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()
    _engine = None
    _session_factory = None


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_engine()
    async with factory() as session:
        yield session


def unique_username() -> str:
    return f"test_user_{uuid.uuid4().hex[:8]}"


def unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@test.ph"


def unique_handle() -> str:
    return f"TestBot_{uuid.uuid4().hex[:8]}"
