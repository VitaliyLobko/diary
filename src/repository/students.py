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


def _students_query(search_by, db: Session):
    query = db.query(Student)
    if search_by:
        query = query.filter(Student.full_name.ilike(f"%{search_by}%"))
    return query


def get_all(search_by, db: Session) -> int:
    # Count over the same filter as get_students, so the pagination total stays
    # correct while searching (it used to count every student regardless).
    return _students_query(search_by, db).count()


def get_students(search_by, limit, offset, db: Session) -> List[Student]:
    return (
        _students_query(search_by, db)
        .order_by(Student.full_name)
        .limit(limit)
        .offset(offset)
        .all()
    )


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
    # Pagination total for get_students_avg_grade: how many distinct students
    # have at least one grade (and a group). A lean COUNT(DISTINCT ...) over the
    # same joins, instead of counting the rows of the full grouped/ordered query.
    total = (
        db.query(func.count(func.distinct(Student.id)))
        .select_from(Grade)
        .join(Student)
        .join(Group)
        .scalar()
    )
    return total or 0


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
    fields = body.model_dump(exclude={"contacts"}, exclude_unset=True)
    for name, value in fields.items():
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
