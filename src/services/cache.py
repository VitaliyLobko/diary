"""Shared Redis client used for caching users and students."""

import redis

from src.conf.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
)


def user_cache_key(email: str) -> str:
    """Redis key under which a user record is cached (see get_current_user)."""
    return f"user:{email}"


def invalidate_user_cache(email: str) -> None:
    """Drop a user's cached record so the next read reloads it from the DB.

    Must be called whenever a user's stored fields change (role, confirmed,
    …); otherwise stale data lingers until the cache TTL expires — e.g. a
    freshly promoted admin keeps being denied because the cached copy still
    carries the old role.
    """
    redis_client.delete(user_cache_key(email))
