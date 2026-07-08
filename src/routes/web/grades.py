"""Server-rendered grades page (Jinja). JSON counterpart:
``src/routes/api/v1/grades.py``.

The page also loads the discipline list to populate the filter dropdown and
accepts an optional ``discipline`` filter that tolerates the empty string an
HTML <select> placeholder submits.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BeforeValidator
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Grade
from src.repository import disciplines as repository_disciplines
from src.repository import grades as repository_grade
from src.repository import students as repository_students
from src.services.pagination import Pagination, pagination_params


def _blank_to_none(value):
    # An HTML <select> placeholder submits an empty string; treat it as "no
    # filter" instead of failing int validation with a 422.
    return None if value == "" else value


# Optional integer query param tolerant of the empty string HTML forms send.
OptionalIntQuery = Annotated[int | None, BeforeValidator(_blank_to_none)]

router = APIRouter(
    prefix="/grades",
    tags=["web:grades"],
    default_response_class=HTMLResponse,
)
templates = Jinja2Templates(directory="templates")


@router.get("/", name="Grades list page")
def grades_page(
    request: Request,
    search_by: str | None = None,
    discipline: OptionalIntQuery = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    grades = repository_grade.get_grades(
        search_by, discipline, pagination.limit, pagination.offset, db
    )
    disciplines = repository_disciplines.get_disciplines(500, 0, db)
    total_count = repository_grade.get_all(search_by, discipline, db)
    # Students populate the "Add grade" modal's dropdown (disciplines is reused
    # from the filter above).
    students = repository_students.get_students(None, 1000, 0, db)
    return templates.TemplateResponse(
        request,
        "grades.html",
        {
            "request": request,
            "grades": grades,
            "disciplines": disciplines,
            "students": students,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Grades",
        },
    )


@router.get("/{grade_id}", name="Grade detail page")
def grade_page(
    request: Request,
    grade_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    grade = db.query(Grade).filter_by(id=grade_id).first()
    if grade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grade with id: {grade_id} not found",
        )
    # Students and disciplines populate the edit modal's dropdowns (this page
    # mirrors student.html's card + edit/delete pattern).
    students = repository_students.get_students(None, 1000, 0, db)
    disciplines = repository_disciplines.get_disciplines(500, 0, db)
    return templates.TemplateResponse(
        request,
        "grade.html",
        {
            "request": request,
            "grade": grade,
            "students": students,
            "disciplines": disciplines,
            "title": "Grade",
        },
    )
