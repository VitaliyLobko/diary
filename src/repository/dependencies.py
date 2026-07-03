from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Discipline, Group, Student, Teacher


async def get_student_by_id(
    student_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    student = db.query(Student).filter_by(id=student_id).first()
    return student


async def get_teacher_by_id(
    teacher_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    teacher = db.query(Teacher).filter_by(id=teacher_id).first()
    return teacher


async def get_group_by_id(
    group_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    group = db.query(Group).filter_by(id=group_id).first()
    return group


async def get_discipline_by_id(
    discipline_id: Annotated[int, Path(ge=1, lt=10_000)], db: Session = Depends(get_db)
):
    discipline = db.query(Discipline).filter_by(id=discipline_id).first()
    return discipline
