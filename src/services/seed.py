"""Demo-data seeding.

Kept out of the route handler so the endpoint stays thin and this logic is
unit-testable. The whole population runs in a single transaction (one commit at
the end), so a failure midway leaves the database untouched instead of
half-seeded — this matters especially together with ``reset``, which wipes the
existing rows first.
"""

from datetime import date, timedelta
from random import Random

from faker import Faker
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.database.models import (
    Contact,
    Discipline,
    Grade,
    Group,
    PersonType,
    Student,
    Teacher,
)

# Delete order that respects foreign keys: children (grades) before the
# students/disciplines they point at, those before groups/teachers. Contacts
# carry no FK, so their position is arbitrary.
WIPE_ORDER = (Grade, Contact, Discipline, Student, Group, Teacher)

# Tables reported back to the caller, in a natural reading order.
_COUNTED = (
    ("teachers", Teacher),
    ("disciplines", Discipline),
    ("groups", Group),
    ("students", Student),
    ("grades", Grade),
    ("contacts", Contact),
)

DISCIPLINES = [
    "Algebra",
    "Biology",
    "Drawing",
    "Art",
    "Chemistry",
    "Geography",
    "Geometry",
    "History",
    "Literature",
    "Mathematics",
    "Music",
    "Physics",
    "Physical education",
    "Computing",
    "Programming",
    "Information technology",
    "Foreign language",
    "Ukrainian language",
    "Astronomy",
    "Ecology",
    "Civics",
    "Economics",
]

GROUP_NAMES = ["a1", "a2", "a3", "b1", "b2", "b3", "c1", "c2", "c3", "d1", "d2", "d3"]

DEFAULT_TEACHERS = 30
DEFAULT_STUDENTS = 150
GRADES_PER_DAY = 5

# Arbitrary constant key for a transaction-scoped advisory lock that serialises
# concurrent seed requests, so two callers can't both pass the "empty?" check
# and double-seed. Released automatically on commit/rollback.
_ADVISORY_LOCK_KEY = 728_144


def student_count(db: Session) -> int:
    """Number of students currently stored — used for the idempotency guard."""
    return db.scalar(select(func.count(Student.id))) or 0


def counts(db: Session) -> dict:
    """Row counts per seeded table."""
    return {name: db.scalar(select(func.count(model.id))) for name, model in _COUNTED}


def _weekdays(year: int):
    """Yield every Mon–Fri ``date`` of the given year."""
    day = date(year, 1, 1)
    end = date(year, 12, 31)
    while day <= end:
        if day.isoweekday() < 6:
            yield day
        day += timedelta(days=1)


def seed_database(
    db: Session,
    *,
    teachers: int = DEFAULT_TEACHERS,
    students: int = DEFAULT_STUDENTS,
    reset: bool = False,
    faker_seed: int | None = None,
) -> dict:
    """Populate demo data atomically and return the resulting row counts.

    Everything below runs in one transaction: intermediate ``flush`` calls only
    assign primary keys; the single ``commit`` at the end makes it all-or-nothing.
    Pass ``faker_seed`` to get reproducible data (handy for tests/screenshots).
    """
    fake = Faker()
    rng = Random(faker_seed)
    if faker_seed is not None:
        Faker.seed(faker_seed)

    # Serialise concurrent seeders (see key comment above).
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})

    # Authoritative idempotency check, *inside* the lock. The route's guard runs
    # before this lock, so two callers can both pass it while the DB is empty;
    # re-checking here is what actually stops a double-seed. ``reset`` wipes
    # regardless, so it skips this short-circuit.
    if not reset and student_count(db) > 0:
        return counts(db)

    if reset:
        for model in WIPE_ORDER:
            db.query(model).delete(synchronize_session=False)
        db.flush()

    teacher_objs = [
        Teacher(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            dob=fake.date_of_birth(minimum_age=25, maximum_age=70),
        )
        for _ in range(teachers)
    ]
    db.add_all(teacher_objs)
    db.flush()
    teacher_ids = [t.id for t in teacher_objs]

    discipline_objs = [
        Discipline(name=name, teacher_id=rng.choice(teacher_ids))
        for name in DISCIPLINES
    ]
    db.add_all(discipline_objs)
    db.flush()
    discipline_ids = [d.id for d in discipline_objs]

    group_objs = [Group(name=name) for name in GROUP_NAMES]
    db.add_all(group_objs)
    db.flush()
    group_ids = [g.id for g in group_objs]

    student_objs = [
        Student(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            group_id=rng.choice(group_ids),
            dob=fake.date_of_birth(minimum_age=6, maximum_age=18),
        )
        for _ in range(students)
    ]
    db.add_all(student_objs)
    db.flush()
    student_ids = [s.id for s in student_objs]

    grade_objs = []
    for day in _weekdays(date.today().year):
        discipline_id = rng.choice(discipline_ids)
        for _ in range(GRADES_PER_DAY):
            grade_objs.append(
                Grade(
                    grade=rng.randint(1, 12),
                    date_of=day,
                    student_id=rng.choice(student_ids),
                    discipline_id=discipline_id,
                )
            )
    db.add_all(grade_objs)

    contact_objs = []
    for person_type, ids in (
        (PersonType.teacher, teacher_ids),
        (PersonType.student, student_ids),
    ):
        for _ in range(len(ids)):
            contact_objs.append(
                Contact(
                    contact_type="email",
                    contact_value=fake.safe_email(),
                    person_types=person_type,
                    person_id=rng.choice(ids),
                )
            )
            contact_objs.append(
                Contact(
                    contact_type="mobile",
                    contact_value=fake.phone_number(),
                    person_types=person_type,
                    person_id=rng.choice(ids),
                )
            )
    db.add_all(contact_objs)

    db.commit()
    return counts(db)
