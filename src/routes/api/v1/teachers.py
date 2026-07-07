"""Teacher JSON API (mounted under ``/api/v1``). See ``api/v1/students.py`` for
the layering rationale."""

from typing import Annotated, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Role, Teacher
from src.repository import teachers as repository_teachers
from src.repository.dependencies import get_teacher_by_id
from src.schemas.teachers import (
    TeacherDetailResponse,
    TeacherModel,
    TeachersIsActiveModel,
    TeachersResponse,
)
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess
from src.services.uploads import delete_upload, save_upload

router = APIRouter(prefix="/teachers", tags=["api:teachers"])

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
    name="List teachers",
)
def list_teachers(
    search_by: str | None = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_teachers.get_teachers(
        search_by, pagination.limit, pagination.offset, db
    )


@router.get(
    "/{teacher_id}",
    response_model=TeacherDetailResponse,
    name="Get teacher by id",
)
def get_teacher(
    teacher_id: Annotated[int, Path(ge=1, lt=10_000)],
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return teacher


@router.put(
    "/{teacher_id}",
    response_model=TeachersResponse,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return repository_teachers.update_teacher(body, teacher, db)


@router.patch(
    "/{teacher_id}/is_active",
    response_model=TeachersResponse,
    name="Set teacher is_active",
    dependencies=[Depends(allowed_operation_update)],
)
def is_active_teacher(
    body: TeachersIsActiveModel,
    teacher: Teacher = Depends(get_teacher_by_id),
    db: Session = Depends(get_db),
):
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return repository_teachers.is_active_teacher(body, teacher, db)


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
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
