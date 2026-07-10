"""Server-rendered teacher pages (Jinja). See ``web/students.py`` for the split
rationale; the JSON counterpart lives in ``src/routes/api/v1/teachers.py``."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Teacher
from src.repository import teachers as repository_teachers
from src.repository.dependencies import get_teacher_by_id
from src.services.pagination import Pagination, pagination_params

router = APIRouter(
    prefix="/teachers",
    tags=["web:teachers"],
    default_response_class=HTMLResponse,
)
templates = Jinja2Templates(directory="templates")


@router.get("/", name="Teachers list page")
def teachers_page(
    request: Request,
    search_by: str | None = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    teachers = repository_teachers.get_teachers(
        search_by, pagination.limit, pagination.offset, db
    )
    total_count = repository_teachers.get_all(search_by, db)
    return templates.TemplateResponse(
        request,
        "teachers.html",
        {
            "request": request,
            "teachers": teachers,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Teachers",
        },
    )


@router.get("/{teacher_id}", name="Teacher detail page")
def teacher_page(
    request: Request,
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return templates.TemplateResponse(
        request,
        "teacher.html",
        {"request": request, "teacher": teacher, "title": "Teacher"},
    )
