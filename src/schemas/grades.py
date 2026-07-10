from datetime import date

from pydantic import BaseModel, Field

# The whole app — seed data, dashboard histogram, averages — assumes the
# national 1–12 scale. Without bounds the API happily stores grade=9999 and
# quietly skews every aggregate that reads it back.
MIN_GRADE = 1
MAX_GRADE = 12


class GradeModel(BaseModel):
    grade: int = Field(ge=MIN_GRADE, le=MAX_GRADE)
    date_of: date
    student_id: int = Field(ge=1)
    discipline_id: int = Field(ge=1)


class GradeResponse(GradeModel):
    id: int
