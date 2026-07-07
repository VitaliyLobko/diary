from datetime import date

from pydantic import BaseModel


class GradeModel(BaseModel):
    grade: int
    date_of: date
    student_id: int
    discipline_id: int


class GradeResponse(GradeModel):
    id: int
