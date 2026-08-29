import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.rate_limiter import rate_limiter
from app.main import app
from app.models.contract import Contract  # noqa: F401
from app.models.job import ExtractionJob  # noqa: F401
from app.schemas.extraction import LLMContractExtraction
from app.services.job_queue import job_queue
import app.services.job_queue as job_queue_module
from app.services.llm.base import BaseLLMClient

# Test SQLite in-memory database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Wire worker pool to in-memory test DB during testing
job_queue_module.AsyncSessionLocal = TestSessionLocal


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test, reset rate limiter, start queue, and drop after."""
    rate_limiter.reset()
    job_queue_module.AsyncSessionLocal = TestSessionLocal
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await job_queue.start()
    yield
    await job_queue.stop()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated AsyncSession for test setup/assertions."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with database dependency override."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class MockLLMClient(BaseLLMClient):
    """Test helper client that returns configurable responses or raises exceptions."""

    def __init__(self, response: LLMContractExtraction = None, side_effect: Exception = None):
        self.response = response
        self.side_effect = side_effect
        self.call_count = 0

    async def extract_contract_data(self, text: str, model: str = None) -> LLMContractExtraction:
        self.call_count += 1
        if self.side_effect:
            raise self.side_effect
        return self.response
