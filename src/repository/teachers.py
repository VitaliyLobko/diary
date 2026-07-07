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


def get_all(db: Session):
    total_teachers = db.query(Teacher).count()
    return total_teachers


def get_teachers(limit, offset, db: Session) -> List[Teacher]:
    teachers = (
        db.query(Teacher).order_by(Teacher.full_name).limit(limit).offset(offset).all()
    )
    return teachers


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
