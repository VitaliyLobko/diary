from typing import List

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from src.database.models import Contact, Grade, Group, PersonType, Student
from src.schemas.students import StudentIsActiveModel, StudentModel


def create_student(body: StudentModel, db: Session):
    # `contacts` is an API-only field and is not a column on the Student table.
    student = Student(**body.model_dump(exclude={"contacts"}))
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def get_all(db: Session):
    total_students = db.query(Student).count()
    return total_students


def get_students(search_by, limit, offset, db: Session) -> List[Student]:
    query = db.query(Student).order_by(Student.full_name)
    if search_by:
        query = query.filter(Student.full_name.ilike(f"%{search_by}%"))
    students = query.limit(limit).offset(offset).all()
    return students


def get_top_10_students(db: Session) -> List[Student]:
    students = (
        db.query(
            Student.id,
            Student.full_name,
            Student.dob,
            Student.created_at,
            Student.updated_at,
            Student.is_active,
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            Group.id.label("group_id"),
            Group.name.label("group_name"),
        )
        .select_from(Student)
        .join(Group)
        .join(Grade)
        .group_by(Student.id, Group.id)
        .order_by(desc(func.avg(Grade.grade)), Student.full_name)
        .limit(10)
        .all()
    )
    return students


def get_all_avg_grade(db: Session) -> int:
    total_avg_grade = (
        db.query(
            Student.id,
            Student.full_name,
            Student.dob,
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            Group.id.label("group_id"),
            Group.name.label("group_name"),
            Student.created_at,
            Student.updated_at,
            Student.is_active,
        )
        .select_from(Grade)
        .join(Student)
        .join(Group)
        .group_by(Student.id, Group.id)
        .order_by(desc(func.avg(Grade.grade)), Student.full_name)
        .count()
    )
    return total_avg_grade


def get_students_avg_grade(limit, offset, db: Session) -> List[Student]:
    students = (
        db.query(
            Student.id,
            Student.full_name,
            Student.dob,
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            Group.id.label("group_id"),
            Group.name.label("group_name"),
            Student.created_at,
            Student.updated_at,
            Student.is_active,
        )
        .select_from(Grade)
        .join(Student)
        .join(Group)
        .group_by(Student.id, Group.id)
        .order_by(desc(func.avg(Grade.grade)), Student.full_name)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return students


def get_student_by_id(student_id: int, db: Session) -> Student | None:
    student = (
        db.query(
            Student.id,
            Student.first_name,
            Student.last_name,
            Student.full_name,
            Student.dob,
            Student.photo,
            func.round(func.avg(Grade.grade), 2).label("avg_grade"),
            Group.id.label("group_id"),
            Group.name.label("group_name"),
            Student.created_at,
            Student.updated_at,
            Student.is_active,
        )
        .select_from(Student)
        .outerjoin(Grade, Grade.student_id == Student.id)
        .outerjoin(Group, Student.group_id == Group.id)
        .group_by(Student.id, Group.id)
        .order_by(desc(func.avg(Grade.grade)), Student.full_name)
        .where(Student.id == student_id)
        .first()
    )

    return student


def get_student_contacts(student_id: int, db: Session) -> List[Contact]:
    contacts = (
        db.query(
            Contact.contact_type,
            Contact.contact_value,
        )
        .filter_by(person_id=student_id)
        .filter_by(person_types=PersonType.student)
        .order_by(desc(Contact.contact_type))
        .all()
    )
    return contacts


def update_student(body: StudentModel, student: Student, db: Session):
    for name, value in body.model_dump(exclude={"contacts"}).items():
        setattr(student, name, value)
    db.commit()
    return student


def is_active_student(body: StudentIsActiveModel, student, db: Session):
    student.is_active = body.is_active
    db.commit()
    return student


def delete_student(student, db: Session):
    db.delete(student)
    db.commit()
    return student
