import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


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
        return self.first_name + " " + self.last_name


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[Optional[bool]] = mapped_column(default=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    last_name: Mapped[Optional[str]] = mapped_column(String(120), default="None")
    dob: Mapped[Optional[date]] = mapped_column()
    photo: Mapped[Optional[str]] = mapped_column(String(255))
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE")
    )
    group: Mapped[Optional["Group"]] = relationship(backref="students")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    @hybrid_property
    def full_name(self):
        return self.first_name + " " + self.last_name


class Contact(Base):
    __tablename__ = "contacts"
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
        ForeignKey("teachers.id", ondelete="CASCADE")
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
        ForeignKey("students.id", ondelete="CASCADE")
    )
    discipline_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("disciplines.id", ondelete="CASCADE")
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
