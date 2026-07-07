from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Discipline, Grade, Group, Student, Teacher


def get_student_by_id(
    student_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    student = db.query(Student).filter_by(id=student_id).first()
    return student


def get_teacher_by_id(
    teacher_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    teacher = db.query(Teacher).filter_by(id=teacher_id).first()
    return teacher


def get_group_by_id(
    group_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    group = db.query(Group).filter_by(id=group_id).first()
    return group


def get_discipline_by_id(
    discipline_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    discipline = db.query(Discipline).filter_by(id=discipline_id).first()
    return discipline


def get_grade_by_id(
    grade_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    grade = db.query(Grade).filter_by(id=grade_id).first()
    return grade
