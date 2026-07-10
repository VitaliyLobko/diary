import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Index, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


def _full_name_py(first: Optional[str], last: Optional[str]) -> str:
    """Python-side ``full_name``. ``first + " " + last`` raised TypeError on NULL."""
    return f"{first or ''} {last or ''}".strip()


def _full_name_sql(first, last):
    """SQL-side ``full_name``, kept byte-for-byte equal to ``_full_name_py``.

    ``concat_ws`` would read better but is only STABLE, so Postgres refuses to
    index it; ``coalesce``/``||``/``btrim`` are IMMUTABLE. The trigram indexes in
    migration ``a7c3e9d21b04`` are built on exactly this expression — change one
    and the ILIKE searches quietly fall back to a sequential scan.
    """
    return func.btrim(func.coalesce(first, "") + " " + func.coalesce(last, ""))


class Role(enum.Enum):
    admin: str = "admin"
    moderator: str = "moderator"
    user: str = "user"


class PersonType(enum.Enum):
    teacher: str = "teacher"
    student: str = "student"


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[Optional[bool]] = mapped_column(default=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    last_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    dob: Mapped[Optional[date]] = mapped_column()
    photo: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    @hybrid_property
    def full_name(self):
        return _full_name_py(self.first_name, self.last_name)

    @full_name.inplace.expression
    @classmethod
    def _full_name_expression(cls):
        return _full_name_sql(cls.first_name, cls.last_name)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[Optional[bool]] = mapped_column(default=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    last_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    dob: Mapped[Optional[date]] = mapped_column()
    photo: Mapped[Optional[str]] = mapped_column(String(255))
    # Postgres does not index foreign keys automatically; this one backs the
    # group filter and the Student→Group joins in every listing.
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    group: Mapped[Optional["Group"]] = relationship(backref="students")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    @hybrid_property
    def full_name(self):
        return _full_name_py(self.first_name, self.last_name)

    @full_name.inplace.expression
    @classmethod
    def _full_name_expression(cls):
        return _full_name_sql(cls.first_name, cls.last_name)


class Contact(Base):
    __tablename__ = "contacts"
    # get_student_contacts filters on (person_id, person_types) together; without
    # this the student detail page sequentially scans every contact row.
    __table_args__ = (Index("ix_contacts_person", "person_id", "person_types"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contact_type: Mapped[str] = mapped_column(String(50))
    contact_value: Mapped[str] = mapped_column(String(255))
    person_id: Mapped[int] = mapped_column()
    person_types: Mapped[Optional[PersonType]] = mapped_column(
        Enum(PersonType), default=PersonType.student
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class Discipline(Base):
    __tablename__ = "disciplines"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    teacher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    teacher: Mapped[Optional["Teacher"]] = relationship(backref="disciplines")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class Grade(Base):
    __tablename__ = "grades"
    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[int] = mapped_column()
    date_of: Mapped[Optional[date]] = mapped_column()
    student_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    discipline_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("disciplines.id", ondelete="CASCADE"), index=True
    )
    student: Mapped[Optional["Student"]] = relationship(backref="grade")
    discipline: Mapped[Optional["Discipline"]] = relationship(backref="grade")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    username: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    confirmed: Mapped[Optional[bool]] = mapped_column(default=False)
    password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )
    roles: Mapped[Optional[Role]] = mapped_column(Enum(Role), default=Role.user)
