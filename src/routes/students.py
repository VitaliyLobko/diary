import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Annotated, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Request,
    UploadFile,
    status,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED

from src.database.db import get_db
from src.database.models import Role, Student
from src.repository import students as repository_students
from src.repository.dependencies import get_student_by_id
from src.schemas.students import (
    StudentIsActiveModel,
    StudentModel,
    StudentsResponse,
    StudentsResponseWithAvgGrade,
)
from src.services.cache import redis_client
from src.services.pagination import Pagination, pagination_params
from src.services.roles import RoleAccess
from src.services.uploads import delete_upload, save_upload

router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="templates")

STUDENT_CACHE_TTL = 60  # seconds

# ``get_student_by_id`` returns a Row carrying a ``date`` (dob), two datetimes
# and a Decimal (avg_grade). JSON has none of those, so we round-trip them by
# name — this keeps ``dob`` a real ``date`` for the template's ``strftime``.
_STUDENT_DATE_FIELDS = ("dob",)
_STUDENT_DATETIME_FIELDS = ("created_at", "updated_at")

allowed_operation_get = RoleAccess([Role.admin, Role.moderator, Role.user])
allowed_operation_create = RoleAccess([Role.admin, Role.moderator])
allowed_operation_update = RoleAccess([Role.admin, Role.moderator])
allowed_operation_remove = RoleAccess([Role.admin])


def _serialize_student(student) -> str:
    """Serialize a student Row to JSON for the Redis cache.

    Deliberately not pickle (``pickle.loads`` on cache data is an RCE risk and
    a pickled ORM Row is fragile). Decimals become floats and dates/datetimes
    become ISO strings so the payload is plain JSON.
    """
    data = dict(student._mapping)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = float(value)
        elif isinstance(value, (date, datetime)):
            data[key] = value.isoformat()
    return json.dumps(data)


def _deserialize_student(raw: bytes) -> SimpleNamespace:
    """Rebuild a cached student (see _serialize_student), restoring date types.

    Returns a ``SimpleNamespace`` so the template can keep using attribute
    access (``student.full_name``, ``student.dob.strftime(...)``, …).
    """
    data = json.loads(raw)
    for field in _STUDENT_DATETIME_FIELDS:
        if data.get(field):
            data[field] = datetime.fromisoformat(data[field])
    for field in _STUDENT_DATE_FIELDS:
        if data.get(field):
            data[field] = date.fromisoformat(data[field])
    return SimpleNamespace(**data)


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
    name="List of all students",
)
def get_students(
    request: Request,
    search_by: str = "",
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    students = repository_students.get_students(
        search_by, pagination.limit, pagination.offset, db
    )
    total_count = repository_students.get_all(search_by, db)
    if students is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="data not found"
        )

    return templates.TemplateResponse(
        request,
        "students.html",
        {
            "request": request,
            "students": students,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Students List",
        },
    )


@router.get(
    "/top_10_students",
    response_model=List[StudentsResponseWithAvgGrade],
    tags=["students"],
)
def top_10_students(request: Request, db: Session = Depends(get_db)):
    students = repository_students.get_top_10_students(db)
    if students is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="data not found"
        )
    return templates.TemplateResponse(
        request,
        "top_10_students.html",
        {"request": request, "students": students, "title": "Top 10 students"},
    )


@router.get(
    "/avg_grade",
    response_model=List[StudentsResponseWithAvgGrade],
    name="List of all students sorting by avg grade",
)
def get_students_avg_grade(
    request: Request,
    pagination: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    students = repository_students.get_students_avg_grade(
        pagination.limit, pagination.offset, db
    )
    total_count = repository_students.get_all_avg_grade(db)
    if students is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="data not found"
        )

    return templates.TemplateResponse(
        request,
        "students_with_grades.html",
        {
            "request": request,
            "students": students,
            "limit": pagination.limit,
            "offset": pagination.offset,
            "total_count": total_count,
            "title": "Avg grades",
        },
    )


@router.get(
    "/{student_id}",
    name="Get student by id",
)
def get_student(
    request: Request,
    student_id: Annotated[int, Path(ge=1, lt=10_000)],
    db: Session = Depends(get_db),
):
    cached = redis_client.get(f"student:{student_id}")
    if cached is not None:
        student = _deserialize_student(cached)
    else:
        student = repository_students.get_student_by_id(student_id, db)
        # Only cache a hit — caching ``None`` would pin a 404 for the whole TTL,
        # so a freshly created student would stay invisible for up to a minute.
        if student is not None:
            redis_client.set(f"student:{student_id}", _serialize_student(student))
            redis_client.expire(f"student:{student_id}", STUDENT_CACHE_TTL)

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id: {student_id} not found",
        )

    contacts = repository_students.get_student_contacts(student_id, db)

    return templates.TemplateResponse(
        request,
        "student.html",
        {
            "request": request,
            "student": student,
            "contacts": contacts,
            "title": "Student",
        },
    )


@router.put(
    "/{student_id}",
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    student_id = student.id
    student = repository_students.update_student(body, student, db)
    redis_client.delete(f"student:{student_id}")
    return student


@router.patch(
    "/{student_id}/is_active",
    name="Set status is_active by student id",
    dependencies=[Depends(allowed_operation_update)],
)
def is_active_student(
    body: StudentIsActiveModel,
    student: Student = Depends(get_student_by_id),
    db: Session = Depends(get_db),
):
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    student_id = student.id
    student = repository_students.is_active_student(body, student, db)
    redis_client.delete(f"student:{student_id}")
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    student_id = student.id
    repository_students.delete_student(student, db)
    redis_client.delete(f"student:{student_id}")


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
    redis_client.delete(f"student:{student.id}")
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
        redis_client.delete(f"student:{student.id}")
    return {"photo": None}
