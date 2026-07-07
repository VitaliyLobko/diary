"""Shared pagination for list endpoints.

Centralises the ``limit``/``offset`` query params and their bounds so every list
route validates them the same way, instead of repeating (and drifting on) the
definition. ``limit`` is clamped to a sane range and ``offset`` cannot go
negative, so out-of-range values fail with a clean 422 rather than reaching the
database.
"""

from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
