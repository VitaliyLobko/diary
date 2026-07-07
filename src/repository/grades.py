from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.models import Discipline, Grade, Student, Teacher
from src.schemas.grades import GradeModel


def create_grade(body: GradeModel, db: Session):
    student = db.query(Student).filter_by(id=body.student_id).first()
    discipline = db.query(Discipline).filter_by(id=body.discipline_id).first()
    if student is None or discipline is None:
        return None
    grade = Grade(**body.model_dump())
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade


def _grades_query(search_by, discipline, db: Session):
    query = (
        db.query(Grade)
        .join(Student, Grade.student_id == Student.id)
        .join(Discipline, Grade.discipline_id == Discipline.id)
        .join(Teacher, Discipline.teacher_id == Teacher.id)
    )
    if search_by:
        query = query.filter(Student.full_name.ilike(f"%{search_by}%"))
    if discipline:
        query = query.filter(Discipline.id == discipline)
    return query


def get_all(search_by, discipline, db: Session):
    return _grades_query(search_by, discipline, db).count()


def get_grades(search_by, discipline, limit, offset, db: Session):
    grades = (
        _grades_query(search_by, discipline, db)
        .with_entities(
            Grade.id,
            Grade.grade,
            Grade.date_of,
            Student.full_name.label("student_fullname"),
            Teacher.full_name.label("teacher_fullname"),
            Discipline.name.label("discipline_name"),
        )
        .order_by(desc(Grade.date_of))
        .limit(limit)
        .offset(offset)
        .all()
    )
    return grades


def update_grade(body: GradeModel, grade, db: Session):
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(grade, name, value)
    db.commit()
    return grade


def delete_grade(grade, db: Session):
    db.delete(grade)
    db.commit()
    return grade
