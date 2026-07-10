"""Shared Redis client used for caching users and students.

Redis here is a *cache*, never the source of truth — Postgres is. Every access
goes through the ``cache_*`` helpers below, which swallow ``RedisError`` and
report a miss, so an unreachable or slow Redis degrades the app to plain DB
reads instead of turning every authenticated request into a 500.
"""

import logging
from typing import Optional

import redis
from redis.exceptions import RedisError

from src.conf.config import settings

logger = logging.getLogger(__name__)

# Without an explicit timeout a wedged Redis (reachable but not answering) hangs
# the worker on socket read until the client gives up — the request never
# returns. Bound both connect and read so a failure surfaces as a fast miss.
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    socket_timeout=settings.redis_socket_timeout,
    socket_connect_timeout=settings.redis_socket_timeout,
)


def cache_get(key: str) -> Optional[bytes]:
    """Read a cached value; treat any Redis failure as a cache miss."""
    try:
        return redis_client.get(key)
    except RedisError:
        logger.warning("Redis GET failed for %s; falling back to DB", key)
        return None


def cache_setex(key: str, ttl: int, value: str) -> None:
    """Store a value with a TTL, atomically. Failures are non-fatal."""
    try:
        # One command, not set+expire: the two-call form can leave a key with no
        # TTL if the process dies (or Redis errors) between them, pinning stale
        # data forever. ``set(ex=...)`` over ``setex``, which redis-py deprecates.
        redis_client.set(key, value, ex=ttl)
    except RedisError:
        logger.warning("Redis SET failed for %s; value not cached", key)


def cache_delete(key: str) -> None:
    """Drop a cached value. Failures are non-fatal (the TTL still bounds staleness)."""
    try:
        redis_client.delete(key)
    except RedisError:
        logger.warning("Redis DEL failed for %s; entry may stay stale until TTL", key)


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
    cache_delete(user_cache_key(email))
