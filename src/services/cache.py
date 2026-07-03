"""Shared Redis client used for caching users and students."""

import redis

from src.conf.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
)
