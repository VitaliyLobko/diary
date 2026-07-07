"""Grade JSON API (mounted under ``/api/v1``).

The list endpoint accepts the same ``search_by``/``discipline`` filters as the
web page but returns clean ``Grade`` rows (see ``repository.grades.list_grades``)
rather than the display Row the template renders.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BeforeValidator
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Grade, Role
from src.repository import grades as repository_grade
from src.repository.dependencies import get_grade_by_id
from src.schemas.grades import GradeModel, GradeResponse
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess


def _blank_to_none(value):
    # An HTML <select> placeholder submits an empty string; treat it as "no
    # filter" instead of failing int validation with a 422.
    return None if value == "" else value


OptionalIntQuery = Annotated[int | None, BeforeValidator(_blank_to_none)]

router = APIRouter(prefix="/grades", tags=["api:grades"])

allowed_operation_create = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=GradeResponse,
    name="Create grade",
    dependencies=[Depends(allowed_operation_create)],
)
def create_grade(body: GradeModel, db: Session = Depends(get_db)):
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
    response_model=List[GradeResponse],
    name="List grades",
)
def list_grades(
    search_by: str | None = None,
    discipline: OptionalIntQuery = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_grade.list_grades(
        search_by, discipline, pagination.limit, pagination.offset, db
    )


@router.get(
    "/{grade_id}",
    response_model=GradeResponse,
    name="Get grade by id",
)
def get_grade(
    grade_id: Annotated[int, Path(ge=1, lt=10_000)],
    grade: Grade = Depends(get_grade_by_id),
    db: Session = Depends(get_db),
):
    if grade is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found"
        )
    return grade


@router.put(
    "/{grade_id}",
    response_model=GradeResponse,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found"
        )
    return repository_grade.update_grade(body, grade, db)


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found"
        )
    repository_grade.delete_grade(grade, db)
