"""Server-rendered student pages (Jinja).

The site's presentation layer: every handler returns an HTML page and is meant
to be opened in a browser, so nothing here declares a ``response_model`` — that
belongs to the JSON API in ``src/routes/api/v1/students.py``. Both layers sit on
the same ``repository_students`` functions, so there is no duplicated logic —
only two different renderings of it.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BeforeValidator
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import groups as repository_groups
from src.repository import students as repository_students
from src.services.cache import cache_get, cache_setex
from src.services.pagination import Pagination, pagination_params

router = APIRouter(
    prefix="/students",
    tags=["web:students"],
    default_response_class=HTMLResponse,
)
templates = Jinja2Templates(directory="templates")

STUDENT_CACHE_TTL = 60  # seconds


def _blank_to_none(value):
    # An HTML <select> placeholder submits an empty string; treat it as "no
    # filter" instead of failing int validation with a 422.
    return None if value == "" else value


# Optional integer query param tolerant of the empty string HTML forms send.
OptionalIntQuery = Annotated[int | None, BeforeValidator(_blank_to_none)]

# ``get_student_by_id`` returns a Row carrying a ``date`` (dob), two datetimes
# and a Decimal (avg_grade). JSON has none of those, so we round-trip them by
# name — this keeps ``dob`` a real ``date`` for the template's ``strftime``.
_STUDENT_DATE_FIELDS = ("dob",)
_STUDENT_DATETIME_FIELDS = ("created_at", "updated_at")


def _serialize_student(student) -> str:
    """Serialize a student Row to JSON for the Redis cache.

    Deliberately not pickle (``pickle.loads`` on cache data is an RCE risk and
    a pickled ORM Row is fragile). Decimals become floats and dates/datetimes
    become ISO strings so the payload is plain JSON.
    """
    data = dict(student._mapping)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, (date, datetime)):
            data[key] = value.isoformat()
    return json.dumps(data)


def _deserialize_student(raw: bytes) -> SimpleNamespace:
    """Rebuild a cached student (see _serialize_student), restoring date types.

    Returns a ``SimpleNamespace`` so the template can keep using attribute
    access (``student.full_name``, ``student.dob.strftime(...)``, …).
    """
    data = json.loads(raw)
    for field in _STUDENT_DATETIME_FIELDS:
        if data.get(field):
            data[field] = datetime.fromisoformat(data[field])
    for field in _STUDENT_DATE_FIELDS:
        if data.get(field):
            data[field] = date.fromisoformat(data[field])
    return SimpleNamespace(**data)


@router.get("/", name="Students list page")
def students_page(
    request: Request,
    search_by: str | None = None,
    group: OptionalIntQuery = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    students = repository_students.get_students(
        search_by, pagination.limit, pagination.offset, db, group=group
    )
    total_count = repository_students.get_all(search_by, db, group=group)
    # Groups populate both the group filter and the "Add student" modal dropdown.
    groups = repository_groups.get_groups(500, 0, db)
    return templates.TemplateResponse(
        request,
        "students.html",
        {
            "request": request,
            "students": students,
            "groups": groups,
            "selected_group": group,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Students",
        },
    )


@router.get("/top_10_students", name="Top 10 students page")
def top_10_students_page(request: Request, db: Session = Depends(get_db)):
    students = repository_students.get_top_10_students(db)
    return templates.TemplateResponse(
        request,
        "top_10_students.html",
        {"request": request, "students": students, "title": "Top 10 students"},
    )


@router.get("/avg_grade", name="Students by average grade page")
def students_avg_grade_page(
    request: Request,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    students = repository_students.get_students_avg_grade(
        pagination.limit, pagination.offset, db
    )
    total_count = repository_students.get_all_avg_grade(db)
    return templates.TemplateResponse(
        request,
        "students_with_grades.html",
        {
            "request": request,
            "students": students,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Students by rating",
        },
    )


@router.get("/{student_id}", name="Student detail page")
def student_page(
    request: Request,
    student_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    cached = cache_get(f"student:{student_id}")
    if cached is not None:
        student = _deserialize_student(cached)
    else:
        student = repository_students.get_student_by_id(student_id, db)
        # Only cache a hit — caching ``None`` would pin a 404 for the whole TTL,
        # so a freshly created student would stay invisible for up to a minute.
        if student is not None:
            cache_setex(
                f"student:{student_id}", STUDENT_CACHE_TTL, _serialize_student(student)
            )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id: {student_id} not found",
        )

    contacts = repository_students.get_student_contacts(student_id, db)

    return templates.TemplateResponse(
        request,
        "student.html",
        {
            "request": request,
            "student": student,
            "contacts": contacts,
            "title": "Student",
        },
    )
