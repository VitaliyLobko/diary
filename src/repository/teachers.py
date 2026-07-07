from typing import List

from sqlalchemy.orm import Session

from src.database.models import Teacher
from src.schemas.teachers import (
    TeacherModel,
    TeachersIsActiveModel,
)


def create_teacher(body: TeacherModel, db: Session):
    teacher = Teacher(**body.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def _teachers_query(search_by, db: Session):
    query = db.query(Teacher)
    if search_by:
        query = query.filter(Teacher.full_name.ilike(f"%{search_by}%"))
    return query


def get_all(search_by, db: Session) -> int:
    # Count over the same filter as get_teachers so the pagination total matches
    # the search results.
    return _teachers_query(search_by, db).count()


def get_teachers(search_by, limit, offset, db: Session) -> List[Teacher]:
    return (
        _teachers_query(search_by, db)
        .order_by(Teacher.full_name)
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_teacher(body: TeacherModel, teacher, db: Session):
    for name, value in body:
        setattr(teacher, name, value)
    db.commit()
    return teacher


def is_active_teacher(body: TeachersIsActiveModel, teacher, db: Session):
    teacher.is_active = body.is_active
    db.commit()
    return teacher


def delete_teacher(teacher, db: Session):
    db.delete(teacher)
    db.commit()
    return teacher
