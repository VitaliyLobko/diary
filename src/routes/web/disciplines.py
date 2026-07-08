"""Server-rendered disciplines page (Jinja). JSON counterpart:
``src/routes/api/v1/disciplines.py``."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import disciplines as repository_disciplines
from src.repository import teachers as repository_teachers
from src.services.pagination import Pagination, pagination_params

router = APIRouter(
    prefix="/disciplines",
    tags=["web:disciplines"],
    default_response_class=HTMLResponse,
)
templates = Jinja2Templates(directory="templates")


@router.get("/", name="Disciplines list page")
def disciplines_page(
    request: Request,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    disciplines = repository_disciplines.get_disciplines(
        pagination.limit, pagination.offset, db
    )
    total_count = repository_disciplines.get_all_disciplines(db)
    # Teachers populate the "Add discipline" modal's dropdown.
    teachers = repository_teachers.get_teachers(None, 500, 0, db)
    return templates.TemplateResponse(
        request,
        "disciplines.html",
        {
            "request": request,
            "disciplines": disciplines,
            "teachers": teachers,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Disciplines List",
        },
    )
