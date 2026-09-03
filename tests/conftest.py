"""
Shared pytest fixtures: boots the real app against an isolated in-memory
SQLite database so every test exercises the real routers and real
SQLAlchemy models end to end. OPENAI_API_KEY is deliberately left unset so
tests prove the AI writer is really called (honest config-error path)
rather than silently mocked.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "")

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import StaticPool

import app.database as database_module

database_module.engine = database_module.create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
database_module.AsyncSessionLocal = database_module.async_sessionmaker(
    database_module.engine, class_=database_module.AsyncSession, expire_on_commit=False
)

from app.main import app  # noqa: E402
from unkey_auth import middleware as unkey_middleware  # noqa: E402
from unkey_auth.client import UnkeyClient  # noqa: E402
from unkey_auth.config import Config  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _dispose_async_engine():
    """
    aiosqlite runs every connection on a **non-daemon** background thread
    (`_connection_worker_thread`) that only stops when the connection /
    engine is disposed. The session-lived `database_module.engine` above is
    never disposed on its own, so that thread outlives the test session,
    the Python process can't reach interpreter shutdown after the last
    test, and a CI runner's `Run tests` step hangs on the never-EOF'd
    stdout pipe until the job timeout (pytest itself finishes in ~2s).
    Dispose it explicitly at session teardown. `asyncio.run` is used
    rather than the pytest-asyncio loop because that loop is already torn
    down by the time this session fixture unwinds.
    """
    yield
    import asyncio

    asyncio.run(database_module.engine.dispose())


@pytest.fixture(autouse=True)
def _unkey_fail_open_by_default(monkeypatch):
    """
    This engine's real .env now has a real UNKEY_ROOT_KEY (2026-08-12) so
    engine-to-engine calls get real verification - but that means
    unkey_auth.config.Config.from_env() would reload it fresh from disk on
    every request (deliberately - see its own docstring), which defeats
    even monkeypatch.delenv("UNKEY_ROOT_KEY", ...): the env var comes back
    the moment anything calls from_env() again. Force a disabled Config
    directly (bypassing from_env()/load_dotenv() entirely) so the rest of
    this suite keeps testing real business logic without needing a real
    Unkey-issued client key for every request. test_unkey_auth.py's own
    tests override this per-test to specifically exercise enforcement.
    """
    monkeypatch.setattr(unkey_middleware, "_client", UnkeyClient(Config(unkey_root_key="")))
    monkeypatch.setattr(unkey_middleware, "_warned_disabled", False)


@pytest_asyncio.fixture
async def client():
    """A fresh database schema and a live ASGI test client for each test."""
    async with database_module.engine.begin() as conn:
        await conn.run_sync(database_module.Base.metadata.drop_all)

    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
