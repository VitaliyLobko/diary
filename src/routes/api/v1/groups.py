"""Group JSON API (mounted under ``/api/v1``)."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Group, Role
from src.repository import groups as repository_group
from src.repository.dependencies import get_group_by_id
from src.schemas.groups import GroupModel, GroupResponse
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess

router = APIRouter(prefix="/groups", tags=["api:groups"])

allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=GroupResponse,
    name="Create group",
    dependencies=[Depends(allowed_operation_create)],
)
def create_group(body: GroupModel, db: Session = Depends(get_db)):
    return repository_group.create_group(body, db)


@router.get(
    "/",
    response_model=List[GroupResponse],
    name="List groups",
)
def list_groups(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_group.get_groups(pagination.limit, pagination.offset, db)


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    name="Get group by id",
)
def get_group(
    group_id: Annotated[int, Path(ge=1)],
    group: Group = Depends(get_group_by_id),
    db: Session = Depends(get_db),
):
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    return group


@router.put(
    "/{group_id}",
    response_model=GroupResponse,
    name="Update group by id",
    dependencies=[Depends(allowed_operation_update)],
)
def update_group(
    body: GroupModel,
    group: Group = Depends(get_group_by_id),
    db: Session = Depends(get_db),
):
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    return repository_group.update_group(body, group, db)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete group by id",
    dependencies=[Depends(allowed_operation_remove)],
)
def delete_group(
    group: Group = Depends(get_group_by_id),
    db: Session = Depends(get_db),
) -> None:
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    repository_group.delete_group(group, db)
