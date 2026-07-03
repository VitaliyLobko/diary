from datetime import date, datetime, timedelta
from random import choice, randint

from faker import Faker
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import (
    Contact,
    Discipline,
    Grade,
    Group,
    Role,
    Student,
    Teacher,
)
from src.services.roles import RoleAccess

router = APIRouter(prefix="/seed", tags=["seed"])

allowed_operation_create = RoleAccess([Role.admin])


def date_range(start: date, end: date) -> list:
    result = []
    current_date = start
    while current_date <= end:
        if current_date.isoweekday() < 6:
            result.append(current_date)
        current_date += timedelta(1)
    return result


@router.get(
    "/",
    tags=["seed"],
    dependencies=[Depends(allowed_operation_create)],
)
async def seed(db: Session = Depends(get_db)):
    # TODO:  if data exist no seed
    disciplines = [
        "Algebra",
        "Biology",
        "Drawing",
        "Chemistry",
        "Geography",
        "Geometry",
        "History",
        "Mathematics ",
        "Music",
        "Physics",
        "Physical education",
        "Computing",
    ]

    groups = ["a1", "a2", "a3", "b1", "b2", "b3"]

    fake = Faker()
    number_of_teachers = 12
    number_of_students = 110

    def seed_teachers():
        for _ in range(number_of_teachers):
            teacher = Teacher(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                dob=fake.date_of_birth(None, 25, 70),
            )
            db.add(teacher)
        db.commit()

    def seed_disciplines():
        teacher_ids = db.scalars(select(Teacher.id)).all()
        for discipline in disciplines:
            db.add(Discipline(name=discipline, teacher_id=choice(teacher_ids)))
        db.commit()

    def seed_groups():
        for group in groups:
            db.add(Group(name=group))
        db.commit()

    def seed_students():
        group_ids = db.scalars(select(Group.id)).all()
        for _ in range(number_of_students):
            student = Student(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                group_id=choice(group_ids),
                dob=fake.date_of_birth(None, 18, 40),
            )
            db.add(student)
        db.commit()

    def seed_grades():
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_date = datetime.strptime("2024-12-31", "%Y-%m-%d")
        d_range = date_range(start=start_date, end=end_date)
        discipline_ids = db.scalars(select(Discipline.id)).all()
        student_ids = db.scalars(select(Student.id)).all()

        for d in d_range:
            random_id_discipline = choice(discipline_ids)
            random_ids_student = [choice(student_ids) for _ in range(5)]
            for student_id in random_ids_student:
                grade = Grade(
                    grade=randint(1, 12),
                    date_of=d,
                    student_id=student_id,
                    discipline_id=random_id_discipline,
                )
                db.add(grade)
        db.commit()

    def seed_contacts():

        student_ids = db.scalars(select(Student.id)).all()
        teacher_ids = db.scalars(select(Teacher.id)).all()

        for _ in range(number_of_teachers):
            contactEmail = Contact(
                contact_type="email",
                contact_value=fake.safe_email(),
                person_types="teacher",
                person_id=choice(teacher_ids),
            )
            db.add(contactEmail)
            db.commit()

            contactMobile = Contact(
                contact_type="mobile",
                contact_value=fake.phone_number(),
                person_types="teacher",
                person_id=choice(teacher_ids),
            )
            db.add(contactMobile)
            db.commit()

        for _ in range(number_of_students):
            contactEmail = Contact(
                contact_type="email",
                contact_value=fake.safe_email(),
                person_types="student",
                person_id=choice(student_ids),
            )
            db.add(contactEmail)
            db.commit()

            contactMobile = Contact(
                contact_type="mobile",
                contact_value=fake.phone_number(),
                person_types="student",
                person_id=choice(student_ids),
            )
            db.add(contactMobile)
            db.commit()

    seed_teachers()
    seed_disciplines()
    seed_groups()
    seed_students()
    seed_grades()
    seed_contacts()
