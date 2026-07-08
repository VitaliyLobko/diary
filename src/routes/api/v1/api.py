"""Aggregates every ``/api/v1`` sub-router into one router.

``main.py`` mounts this under the ``/api/v1`` prefix, so migrating the next
resource to the JSON API is a single ``include_router`` line here rather than a
change in ``main.py``.
"""

from fastapi import APIRouter

from src.routes.api.v1 import (
    dashboard,
    disciplines,
    grades,
    groups,
    students,
    teachers,
)

router = APIRouter()
router.include_router(students.router)
router.include_router(teachers.router)
router.include_router(groups.router)
router.include_router(disciplines.router)
router.include_router(grades.router)
router.include_router(dashboard.router)
