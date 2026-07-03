from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.database.models import Discipline, Grade, Group, Student, Teacher
from src.schemas.grades import GradeModel


async def create_grade(body: GradeModel, db: Session):
    grade = Group(**body.model_dump())
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade


async def get_all(db: Session):
    all_grades = db.query(Grade).count()
    return all_grades


# FIXME: need fix search criteria
async def get_grades(search_by, discipline, limit, offset, db: Session):
    if search_by:
        grades = (
            db.query(
                Grade.id,
                Grade.grade,
                Grade.date_of,
                Student.full_name.label("student_fullname"),
                Teacher.full_name.label("teacher_fullname"),
                Discipline.name.label("discipline_name"),
            )
            .join(Student)
            .join(Discipline)
            .join(Teacher)
            .filter(Student.full_name.ilike(f"%{search_by}%"))
            .order_by(desc(Grade.date_of))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return grades
    else:
        grades = (
            db.query(
                Grade.id,
                Grade.grade,
                Grade.date_of,
                Student.full_name.label("student_fullname"),
                Teacher.full_name.label("teacher_fullname"),
                Discipline.name.label("discipline_name"),
            )
            .join(Student)
            .join(Discipline)
            .join(Teacher)
            .order_by(desc(Grade.date_of))
            .limit(limit)
            .offset(offset)
            .all()
        )

    if discipline:
        grades = (
            (
                db.query(
                    Grade.id,
                    Grade.grade,
                    Grade.date_of,
                    Student.full_name.label("student_fullname"),
                    Teacher.full_name.label("teacher_fullname"),
                    Discipline.id,
                    Discipline.name.label("discipline_name"),
                )
            )
            .join(Student)
            .join(Discipline)
            .join(Teacher)
            .where(Discipline.id == discipline)
            .order_by(desc(Grade.date_of))
            .limit(limit)
            .offset(offset)
            .all()
        )

    return grades
