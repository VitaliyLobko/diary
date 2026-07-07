from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Role, Teacher
from src.repository import teachers as repository_teachers
from src.repository.dependencies import get_teacher_by_id
from src.schemas.teachers import (
    TeacherModel,
    TeachersIsActiveModel,
    TeachersResponse,
)
from src.services.roles import RoleAccess
from src.services.uploads import delete_upload, save_upload

router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory="templates")

allowed_operation_get = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=TeachersResponse,
    name="Create teacher",
    dependencies=[Depends(allowed_operation_create)],
)
def create_teacher(body: TeacherModel, db: Session = Depends(get_db)):
    teacher = repository_teachers.create_teacher(body, db)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="something wrong"
        )

    return teacher


@router.get(
    "/",
    response_model=List[TeachersResponse],
    name="List of all teachers",
)
def get_teachers(
    request: Request,
    limit: int = Query(20, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    teachers = repository_teachers.get_teachers(limit, offset, db)
    total_count = repository_teachers.get_all(db)
    if teachers is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="data not found"
        )

    return templates.TemplateResponse(
        request,
        "teachers.html",
        {
            "request": request,
            "teachers": teachers,
            "limit": limit,
            "offset": offset,
            "total_count": total_count,
            "title": "Teacher List",
        },
    )


@router.get(
    "/{teacher_id}",
    name="Get teacher by id",
)
def get_teacher(
    request: Request,
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found",
        )
    return templates.TemplateResponse(
        request,
        "teacher.html",
        {"request": request, "teacher": teacher, "title": "Teacher"},
    )


@router.put(
    "/{teacher_id}",
    name="Update teacher by id",
    dependencies=[Depends(allowed_operation_update)],
)
def update_teacher(
    body: TeacherModel,
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found",
        )
    teacher = repository_teachers.update_teacher(body, teacher, db)
    return teacher


@router.patch(
    "/{teacher_id}/is_active",
    response_model=TeachersResponse,
    name="Set status is_active by teacher id",
    dependencies=[Depends(allowed_operation_update)],
)
def is_active_teacher(
    body: TeachersIsActiveModel,
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found",
        )
    teacher = repository_teachers.is_active_teacher(body, teacher, db)
    return teacher


@router.delete(
    "/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete teacher by id",
    dependencies=[Depends(allowed_operation_remove)],
)
def delete_teacher(
    teacher: Teacher = Depends(get_teacher_by_id), db: Session = Depends(get_db)
) -> None:
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher not found",
        )
    repository_teachers.delete_teacher(teacher, db)


@router.post(
    "/{teacher_id}/photo",
    name="Upload teacher photo",
    dependencies=[Depends(allowed_operation_update)],
)
def upload_teacher_photo(
    file: UploadFile = File(...),
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    teacher.photo = save_upload(file, "teacher", teacher.id, old=teacher.photo)
    db.commit()
    return {"photo": teacher.photo}


@router.delete(
    "/{teacher_id}/photo",
    name="Delete teacher photo",
    dependencies=[Depends(allowed_operation_update)],
)
def delete_teacher_photo(
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if teacher.photo:
        delete_upload(teacher.photo)
        teacher.photo = None
        db.commit()
    return {"photo": None}
