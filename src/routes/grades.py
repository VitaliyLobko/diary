from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Grade, Role
from src.repository import disciplines as repository_disciplines
from src.repository import grades as repository_grade
from src.repository.dependencies import get_grade_by_id
from src.schemas.grades import GradeModel
from src.services.pagination import Pagination, pagination_params
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
def create_grade(
    body: GradeModel,
    db: Session = Depends(get_db),
):
    grade = repository_grade.create_grade(body, db)
    if grade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Student with id: {body.student_id} or "
                f"discipline with id: {body.discipline_id} not found"
            ),
        )
    return grade


@router.get(
    "/",
    name="List of all grades",
)
def get_grades(
    request: Request,
    search_by: str = "",
    discipline: str = "",
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    grades = repository_grade.get_grades(
        search_by, discipline, pagination.limit, pagination.offset, db
    )
    disciplines = repository_disciplines.get_disciplines(500, 0, db)
    total_count = repository_grade.get_all(search_by, discipline, db)
    if grades is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    return templates.TemplateResponse(
        request,
        "grades.html",
        {
            "request": request,
            "grades": grades,
            "disciplines": disciplines,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Grades",
        },
    )


@router.put(
    "/{grade_id}",
    name="Update grade by id",
    dependencies=[Depends(allowed_operation_update)],
)
def update_grade(
    body: GradeModel,
    grade: Grade = Depends(get_grade_by_id),
    db: Session = Depends(get_db),
):
    if grade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found",
        )
    grade = repository_grade.update_grade(body, grade, db)
    return grade


@router.delete(
    "/{grade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete grade by id",
    dependencies=[Depends(allowed_operation_remove)],
)
def delete_grade(
    grade: Grade = Depends(get_grade_by_id),
    db: Session = Depends(get_db),
) -> None:
    if grade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grade not found",
        )
    repository_grade.delete_grade(grade, db)
