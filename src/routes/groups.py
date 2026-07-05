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
from src.database.models import Group, Role
from src.repository import groups as repository_group
from src.repository.dependencies import get_group_by_id
from src.schemas.groups import GroupModel, GroupResponse
from src.services.roles import RoleAccess

router = APIRouter(prefix="/groups", tags=["groups"])
templates = Jinja2Templates(directory="templates")

allowed_operation_get = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    name="Create group",
    dependencies=[Depends(allowed_operation_create)],
)
async def create_group(body: GroupModel, db: Session = Depends(get_db)):
    group = await repository_group.create_group(body, db)
    return group


@router.get(
    "/",
    response_model=List[GroupResponse],
    name="List of all groups",
)
async def get_groups(
    request: Request,
    limit: int = Query(20, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    groups = await repository_group.get_groups(limit, offset, db)
    total_count = await repository_group.get_all(db)

    if groups is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    return templates.TemplateResponse(
        request,
        "groups.html",
        {
            "request": request,
            "groups": groups,
            "limit": limit,
            "offset": offset,
            "total_count": total_count,
            "title": "Groups",
        },
    )


@router.put(
    "/{group_id}",
    name="Update group by id",
    dependencies=[Depends(allowed_operation_update)],
)
async def update_group(
    body: GroupModel,
    group: Group = Depends(get_group_by_id),
    db: Session = Depends(get_db),
):
    group = await repository_group.update_group(body, group, db)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id: {group} not found",
        )
    return group


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete group by id",
    dependencies=[Depends(allowed_operation_remove)],
)
async def delete_group(
    group: Group = Depends(get_group_by_id),
    db: Session = Depends(get_db),
) -> None:

    group = await repository_group.delete_group(group, db)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
