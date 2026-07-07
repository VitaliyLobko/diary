from datetime import date, datetime
from typing import Annotated, Optional

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, ConfigDict


class TeacherModel(BaseModel):
    is_active: bool = True
    first_name: Annotated[str, MinLen(2), MaxLen(250)]
    last_name: Annotated[str, MinLen(2), MaxLen(250)]
    dob: date


class TeachersResponse(BaseModel):
    id: int
    is_active: bool = True
    full_name: str
    dob: date
    created_at: datetime
    updated_at: datetime


class TeacherDetailResponse(TeachersResponse):
    """Single-teacher payload for the JSON API (``GET /api/v1/teachers/{id}``).

    Adds the split name and photo the list view omits, mirroring
    ``StudentDetailResponse``.
    """

    first_name: str
    last_name: str
    photo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeachersIsActiveModel(BaseModel):
    is_active: bool = True
