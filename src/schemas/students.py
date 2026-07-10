from datetime import date, datetime
from typing import Annotated, List, Optional

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, ConfigDict

from src.schemas.common import Dob
from src.schemas.contacts import ContactModel


class StudentModel(BaseModel):
    is_active: bool = True
    first_name: Annotated[str, MinLen(2), MaxLen(250)]
    last_name: Annotated[str, MinLen(2), MaxLen(250)]
    dob: Dob
    group_id: int
    contacts: Optional[ContactModel] = None


class StudentIsActiveModel(BaseModel):
    is_active: bool = True


class StudentsResponse(BaseModel):
    id: int
    is_active: bool = True
    full_name: str
    dob: date
    group_id: int
    created_at: datetime
    updated_at: datetime


class StudentsResponseWithAvgGrade(StudentsResponse):
    avg_grade: float
    group_name: str


class StudentContactResponse(BaseModel):
    contact_type: str
    contact_value: str

    model_config = ConfigDict(from_attributes=True)


class StudentDetailResponse(BaseModel):
    """Single-student payload for the JSON API (``GET /api/v1/students/{id}``).

    Carries the extra fields the mobile client needs but the list view omits:
    the split name, photo, computed ``avg_grade`` and the student's contacts.
    ``avg_grade``/``group_*`` are optional because a student with no grades or
    no group yields NULLs from the aggregate query.
    """

    id: int
    is_active: bool
    first_name: str
    last_name: str
    full_name: str
    dob: date
    photo: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    avg_grade: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    contacts: List[StudentContactResponse] = []

    model_config = ConfigDict(from_attributes=True)
