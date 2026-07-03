from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Role
from src.repository import disciplines as repository_disciplines
from src.repository import grades as repository_grade
from src.schemas.grades import GradeModel, GradeResponse
from src.services.roles import RoleAccess

router = APIRouter(prefix="/grades", tags=["grades"])
templates = Jinja2Templates(directory="templates")


allowed_operation_get = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_create = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    name="Create grade",
    dependencies=[Depends(allowed_operation_create)],
)
async def create_grade(
    body: GradeModel,
    db: Session = Depends(get_db),
):
    group = await repository_grade.create_grade(body, db)
    return group


@router.get(
    "/",
    response_model=List[GradeResponse],
    name="List of all grades",
)
async def get_grades(
    request: Request,
    search_by: str = "",
    discipline="",
    limit: int = Query(20, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    grades = await repository_grade.get_grades(search_by, discipline, limit, offset, db)
    disciplines = await repository_disciplines.get_disciplines(limit, offset, db)
    # TODO: teachers =  await repository_disciplines.get_teachers(db)
    total_count = await repository_grade.get_all(db)
    if grades is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    return templates.TemplateResponse(
        "grades.html",
        {
            "request": request,
            "grades": grades,
            "disciplines": disciplines,
            "limit": limit,
            "offset": offset,
            "total_count": total_count,
            "title": "Grades",
        },
    )


# TODO: add update, delete
