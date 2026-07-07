from datetime import date, datetime
from typing import Annotated, Optional

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel

from src.schemas.contacts import ContactModel


class StudentModel(BaseModel):
    is_active: bool = True
    first_name: Annotated[str, MinLen(2), MaxLen(250)]
    last_name: Annotated[str, MinLen(2), MaxLen(250)]
    dob: date
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
