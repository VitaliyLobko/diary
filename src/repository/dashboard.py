"""Aggregation queries backing the home dashboard.

Read-only summary statistics over the whole school: headline counts, the overall
average grade, the grade distribution, per-discipline and per-group averages, the
strongest students and the most recent grades. Both presentation layers sit on
these functions — the Jinja home page (``src/routes/web/dashboard.py``) and the
JSON API (``src/routes/api/v1/dashboard.py``) — so there is a single source of
truth for the numbers.
"""

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.database.models import (
    Discipline,
    Grade,
    Group,
    Student,
    Teacher,
)


def get_counts(db: Session) -> dict:
    """Headline row counts for the stat tiles."""
    return {
        "students": db.scalar(func.count(Student.id)) or 0,
        "teachers": db.scalar(func.count(Teacher.id)) or 0,
        "groups": db.scalar(func.count(Group.id)) or 0,
        "disciplines": db.scalar(func.count(Discipline.id)) or 0,
        "grades": db.scalar(func.count(Grade.id)) or 0,
    }


def get_overall_average(db: Session) -> float | None:
    """Mean of every grade on the 1–12 scale, or ``None`` when there are none."""
    avg = db.scalar(func.round(func.avg(Grade.grade), 2))
    return float(avg) if avg is not None else None


def get_grade_distribution(db: Session) -> list[dict]:
    """How many grades fall on each value 1–12.

    Every point on the scale is represented (missing ones as ``count == 0``) so
    the template can render a stable 12-bar histogram regardless of the data.
    """
    rows = dict(
        db.query(Grade.grade, func.count(Grade.id))
        .group_by(Grade.grade)
        .all()
    )
    return [{"grade": value, "count": rows.get(value, 0)} for value in range(1, 13)]


def get_avg_by_discipline(db: Session, limit: int = 10) -> list[dict]:
    """Average grade per discipline, best first (only disciplines with grades)."""
    rows = (
        db.query(
            Discipline.name.label("name"),
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            func.count(Grade.id).label("grade_count"),
        )
        .join(Grade, Grade.discipline_id == Discipline.id)
        .group_by(Discipline.id)
        .order_by(desc(func.avg(Grade.grade)), Discipline.name)
        .limit(limit)
        .all()
    )
    return [
        {"name": r.name, "avg_grade": float(r.avg_grade), "grade_count": r.grade_count}
        for r in rows
    ]


def get_avg_by_group(db: Session, limit: int = 12) -> list[dict]:
    """Average grade per group with how many of its students have grades."""
    rows = (
        db.query(
            Group.name.label("name"),
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            func.count(func.distinct(Student.id)).label("student_count"),
        )
        .select_from(Group)
        .join(Student, Student.group_id == Group.id)
        .join(Grade, Grade.student_id == Student.id)
        .group_by(Group.id)
        .order_by(desc(func.avg(Grade.grade)), Group.name)
        .limit(limit)
        .all()
    )
    return [
        {
            "name": r.name,
            "avg_grade": float(r.avg_grade),
            "student_count": r.student_count,
        }
        for r in rows
    ]


def get_top_students(db: Session, limit: int = 5) -> list[dict]:
    """Highest-averaging students (needs a group and at least one grade)."""
    rows = (
        db.query(
            Student.id.label("id"),
            Student.full_name.label("full_name"),
            Group.name.label("group_name"),
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
        )
        .select_from(Student)
        .join(Group, Student.group_id == Group.id)
        .join(Grade, Grade.student_id == Student.id)
        .group_by(Student.id, Group.id)
        .order_by(desc(func.avg(Grade.grade)), Student.full_name)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "group_name": r.group_name,
            "avg_grade": float(r.avg_grade),
        }
        for r in rows
    ]


def get_recent_grades(db: Session, limit: int = 8) -> list[dict]:
    """The most recently dated grades, with student and discipline names."""
    rows = (
        db.query(
            Grade.grade.label("grade"),
            Grade.date_of.label("date_of"),
            Student.full_name.label("student_name"),
            Discipline.name.label("discipline_name"),
        )
        .join(Student, Grade.student_id == Student.id)
        .join(Discipline, Grade.discipline_id == Discipline.id)
        .order_by(desc(Grade.date_of), desc(Grade.id))
        .limit(limit)
        .all()
    )
    return [
        {
            "grade": r.grade,
            "date_of": r.date_of,
            "student_name": r.student_name,
            "discipline_name": r.discipline_name,
        }
        for r in rows
    ]


def get_dashboard(db: Session) -> dict:
    """Everything the home dashboard needs, in one call."""
    return {
        "counts": get_counts(db),
        "overall_average": get_overall_average(db),
        "grade_distribution": get_grade_distribution(db),
        "avg_by_discipline": get_avg_by_discipline(db),
        "avg_by_group": get_avg_by_group(db),
        "top_students": get_top_students(db),
        "recent_grades": get_recent_grades(db),
    }
