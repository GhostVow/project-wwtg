"""Dependency injection: database session, Redis client."""

from typing import AsyncGenerator, Any


async def get_db() -> AsyncGenerator[Any, None]:
    """Get async database session.
    
    W1: Returns None (no real DB connection).
    W2: Will yield AsyncSession from SQLAlchemy async engine.
    """
    yield None


async def get_redis() -> Any:
    """Get Redis client.
    
    W1: Returns None (no real Redis connection).
    W2: Will return aioredis client instance.
    """
    return None
