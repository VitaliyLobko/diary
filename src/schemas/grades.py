from datetime import datetime

from pydantic import BaseModel


class GradeModel(BaseModel):
    grade: str
    date_of: datetime
    student_fullname: str
    teacher_fullname: str


class GradeResponse(GradeModel):
    id: int
