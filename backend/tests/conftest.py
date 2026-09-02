import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import uuid

from app.main import app
from app.api.deps import get_db, get_current_user
from app.db.models import User

# --- Test DB Config for Integration Tests ---
# This uses the REAL database (port 5432) as requested by the user.
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/raq_chatbot"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture
async def integration_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        # Optionally cleanup or rollback after tests
        await session.rollback()

@pytest.fixture
async def integration_client(integration_db) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield integration_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
        
    app.dependency_overrides.clear()

# --- Mocks for Unit Tests ---
@pytest.fixture
def mock_db() -> AsyncMock:
    """Provides a mocked database session."""
    session = AsyncMock(spec=AsyncSession)
    
    # Configure scalar_one_or_none, execute, etc.
    # Default behavior: scalar_one_or_none returns None (e.g. user not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars().all.return_value = []
    
    session.execute.return_value = mock_result

    # Simulate SQLAlchemy assigning a default ID when an object is added
    def mock_add(obj):
        import uuid
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
    
    session.add.side_effect = mock_add
    
    return session

@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash="fakehash",
        created_at=datetime.now(timezone.utc)
    )

@pytest.fixture
async def mock_client(mock_db, test_user) -> AsyncGenerator[AsyncClient, None]:
    """Client for unit testing API routes without hitting a real DB."""
    async def override_get_db():
        yield mock_db
        
    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
        
    app.dependency_overrides.clear()
