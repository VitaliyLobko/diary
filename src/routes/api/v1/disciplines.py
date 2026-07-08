"""Discipline JSON API (mounted under ``/api/v1``)."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Discipline, Role
from src.repository import disciplines as repository_disciplines
from src.repository.dependencies import get_discipline_by_id
from src.schemas.disciplines import DisciplineModel, DisciplineResponse
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess

router = APIRouter(prefix="/disciplines", tags=["api:disciplines"])

allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=DisciplineResponse,
    name="Create discipline",
    dependencies=[Depends(allowed_operation_create)],
)
def create_discipline(body: DisciplineModel, db: Session = Depends(get_db)):
    discipline = repository_disciplines.create_discipline(body, db)
    if discipline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher with id: {body.teacher_id} not found",
        )
    return discipline


@router.get(
    "/",
    response_model=List[DisciplineResponse],
    name="List disciplines",
)
def list_disciplines(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_disciplines.list_disciplines(
        pagination.limit, pagination.offset, db
    )


@router.get(
    "/{discipline_id}",
    response_model=DisciplineResponse,
    name="Get discipline by id",
)
def get_discipline(
    discipline_id: Annotated[int, Path(ge=1)],
    discipline: Discipline = Depends(get_discipline_by_id),
    db: Session = Depends(get_db),
):
    if discipline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found"
        )
    return discipline


@router.put(
    "/{discipline_id}",
    response_model=DisciplineResponse,
    name="Update discipline by id",
    dependencies=[Depends(allowed_operation_update)],
)
def update_discipline(
    body: DisciplineModel,
    discipline: Discipline = Depends(get_discipline_by_id),
    db: Session = Depends(get_db),
):
    if discipline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found"
        )
    return repository_disciplines.update_discipline(body, discipline, db)


@router.delete(
    "/{discipline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete discipline by id",
    dependencies=[Depends(allowed_operation_remove)],
)
def delete_discipline(
    discipline: Discipline = Depends(get_discipline_by_id),
    db: Session = Depends(get_db),
) -> None:
    if discipline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found"
        )
    repository_disciplines.delete_discipline(discipline, db)
