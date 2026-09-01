"""
Async SQLAlchemy engine, session factory, and LangGraph checkpointer.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# ── Async Engine ─────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

# ── Session Factory ──────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:
    """Dependency injection for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        yield session


# ── LangGraph Postgres Checkpointer ─────────────────────────
async def get_checkpointer():
    """
    Create and return an AsyncPostgresSaver for LangGraph.
    Uses the same DATABASE_URL but with the raw psycopg connection string.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    # Convert asyncpg URL to psycopg-compatible URL for the checkpointer
    # asyncpg: postgresql+asyncpg://...
    # psycopg: postgresql://...
    pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
    await checkpointer.setup()
    return checkpointer
