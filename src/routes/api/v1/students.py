"""Student JSON API (mounted under ``/api/v1``).

The programmatic surface consumed by the mobile app (and any other client). In
contrast to the web layer, every handler here returns JSON and declares an
honest ``response_model`` so the OpenAPI schema at ``/docs`` describes exactly
what a client receives. Business logic lives in ``repository_students``; this
module only maps HTTP to it and shapes the response.
"""

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
from src.database.models import Role, Student
from src.repository import students as repository_students
from src.repository.dependencies import get_student_by_id
from src.schemas.students import (
    StudentDetailResponse,
    StudentIsActiveModel,
    StudentModel,
    StudentsResponse,
    StudentsResponseWithAvgGrade,
)
from src.services.cache import cache_delete
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess
from src.services.uploads import delete_upload, save_upload

router = APIRouter(prefix="/students", tags=["api:students"])

allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


def _invalidate(student_id: int) -> None:
    """Drop the web layer's cached detail row so it can't serve stale data.

    The single-student page caches ``student:{id}`` for a minute; any mutation
    here must purge it, otherwise an edit made via the API would stay invisible
    on the site until the TTL lapses.
    """
    cache_delete(f"student:{student_id}")


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    response_model=StudentsResponse,
    name="Create student",
    dependencies=[Depends(allowed_operation_create)],
)
def create_student(body: StudentModel, db: Session = Depends(get_db)):
    student = repository_students.create_student(body, db)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="something wrong"
        )
    return student


@router.get(
    "/",
    response_model=List[StudentsResponse],
    name="List students",
)
def list_students(
    search_by: str | None = None,
    group: int | None = None,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_students.get_students(
        search_by, pagination.limit, pagination.offset, db, group=group
    )


@router.get(
    "/top_10_students",
    response_model=List[StudentsResponseWithAvgGrade],
    name="Top 10 students by average grade",
)
def top_10_students(db: Session = Depends(get_db)):
    return repository_students.get_top_10_students(db)


@router.get(
    "/avg_grade",
    response_model=List[StudentsResponseWithAvgGrade],
    name="List students by average grade",
)
def list_students_avg_grade(
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return repository_students.get_students_avg_grade(
        pagination.limit, pagination.offset, db
    )


@router.get(
    "/{student_id}",
    response_model=StudentDetailResponse,
    name="Get student by id",
)
def get_student(
    student_id: Annotated[int, Path(ge=1)],
    db: Session = Depends(get_db),
):
    student = repository_students.get_student_by_id(student_id, db)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id: {student_id} not found",
        )
    contacts = repository_students.get_student_contacts(student_id, db)
    data = dict(student._mapping)
    data["contacts"] = contacts
    return StudentDetailResponse.model_validate(data)


@router.put(
    "/{student_id}",
    response_model=StudentsResponse,
    name="Update student by id",
    dependencies=[Depends(allowed_operation_update)],
)
def update_student(
    body: StudentModel,
    student: Student = Depends(get_student_by_id),
    db: Session = Depends(get_db),
):
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    student_id = student.id
    student = repository_students.update_student(body, student, db)
    _invalidate(student_id)
    return student


@router.patch(
    "/{student_id}/is_active",
    response_model=StudentsResponse,
    name="Set student is_active",
    dependencies=[Depends(allowed_operation_update)],
)
def is_active_student(
    body: StudentIsActiveModel,
    student: Student = Depends(get_student_by_id),
    db: Session = Depends(get_db),
):
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    student_id = student.id
    student = repository_students.is_active_student(body, student, db)
    _invalidate(student_id)
    return student


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Delete student by id",
    dependencies=[Depends(allowed_operation_remove)],
)
def delete_student(
    student: Student = Depends(get_student_by_id), db: Session = Depends(get_db)
) -> None:
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    student_id = student.id
    repository_students.delete_student(student, db)
    _invalidate(student_id)


@router.post(
    "/{student_id}/photo",
    name="Upload student photo",
    dependencies=[Depends(allowed_operation_update)],
)
def upload_student_photo(
    file: UploadFile = File(...),
    student: Student = Depends(get_student_by_id),
    db: Session = Depends(get_db),
):
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    student.photo = save_upload(file, "student", student.id, old=student.photo)
    db.commit()
    _invalidate(student.id)
    return {"photo": student.photo}


@router.delete(
    "/{student_id}/photo",
    name="Delete student photo",
    dependencies=[Depends(allowed_operation_update)],
)
def delete_student_photo(
    student: Student = Depends(get_student_by_id),
    db: Session = Depends(get_db),
):
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if student.photo:
        delete_upload(student.photo)
        student.photo = None
        db.commit()
        _invalidate(student.id)
    return {"photo": None}
