"""
Database configuration and session management.

Provides async SQLAlchemy setup with connection pooling and session handling.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

# Base class for declarative models
Base = declarative_base()

# Global engine and session factory (initialized in init_db)
_async_engine = None
_async_session_factory = None
_sync_engine = None
_sync_session_factory = None


def init_db() -> None:
    """
    Initialize database engines and session factories.

    Should be called once during application startup.
    """
    global _async_engine, _async_session_factory, _sync_engine, _sync_session_factory

    settings = get_settings()
    database_url = settings.get_database_url_for_sqlalchemy()

    # Create async engine
    _async_engine = create_async_engine(
        database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )

    # Create async session factory
    _async_session_factory = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # For migrations and sync operations, create sync engine
    sync_database_url = database_url.replace("+aiosqlite", "")
    _sync_engine = create_engine(
        sync_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )

    _sync_session_factory = sessionmaker(
        bind=_sync_engine,
        class_=Session,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage:
        ```python
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """
    Get a sync database session (for migrations and CLI tools).

    Returns:
        SQLAlchemy Session
    """
    if _sync_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    return _sync_session_factory()


async def create_tables() -> None:
    """
    Create all database tables.

    Should be called during application startup in development.
    In production, use Alembic migrations instead.
    """
    if _async_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data! Use only in development/testing.
    """
    if _async_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """
    Close database connections.

    Should be called during application shutdown.
    """
    global _async_engine, _sync_engine

    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None

    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
