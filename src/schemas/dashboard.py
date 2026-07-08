from datetime import date

from pydantic import BaseModel


class DashboardCounts(BaseModel):
    students: int
    teachers: int
    groups: int
    disciplines: int
    grades: int


class GradeBucket(BaseModel):
    grade: int
    count: int


class DisciplineAverage(BaseModel):
    name: str
    avg_grade: float
    grade_count: int


class GroupAverage(BaseModel):
    name: str
    avg_grade: float
    student_count: int


class TopStudent(BaseModel):
    id: int
    full_name: str
    group_name: str
    avg_grade: float


class RecentGrade(BaseModel):
    grade: int
    date_of: date
    student_name: str
    discipline_name: str


class DashboardResponse(BaseModel):
    counts: DashboardCounts
    overall_average: float | None
    grade_distribution: list[GradeBucket]
    avg_by_discipline: list[DisciplineAverage]
    avg_by_group: list[GroupAverage]
    top_students: list[TopStudent]
    recent_grades: list[RecentGrade]
