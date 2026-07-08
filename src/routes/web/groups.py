"""Server-rendered groups page (Jinja). JSON counterpart:
``src/routes/api/v1/groups.py``."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Group
from src.repository import groups as repository_group
from src.services.pagination import Pagination, pagination_params

router = APIRouter(
    prefix="/groups",
    tags=["web:groups"],
    default_response_class=HTMLResponse,
)
templates = Jinja2Templates(directory="templates")


@router.get("/", name="Groups list page")
def groups_page(
    request: Request,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    groups = repository_group.get_groups(pagination.limit, pagination.offset, db)
    total_count = repository_group.get_all(db)
    return templates.TemplateResponse(
        request,
        "groups.html",
        {
            "request": request,
            "groups": groups,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Groups",
        },
    )


@router.get("/{group_id}", name="Group detail page")
def group_page(
    request: Request,
    group_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter_by(id=group_id).first()
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id: {group_id} not found",
        )
    return templates.TemplateResponse(
        request,
        "group.html",
        {"request": request, "group": group, "title": "Group"},
    )
