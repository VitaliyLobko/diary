"""Regressions for the correctness bugs fixed in the audit's 🟠 section.

Each test pins a behaviour that used to be silently wrong: a user stored under
the wrong column, grades disappearing behind an inner join, an input field the
API advertised but dropped, DB errors mislabelled as 400s with SQL in the body,
and a role claim frozen at login surviving a demotion.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

from src.database.db import get_db
from src.database.models import Discipline, Grade, Group, Role, Student, User
from src.repository import grades as repo_grades
from src.schemas.students import StudentModel
from src.services.auth import hash_handler
from src.services.cache import invalidate_user_cache


def test_create_user_uses_email_not_username(client, session, monkeypatch):
    monkeypatch.setattr("src.services.email.send_email", lambda *a, **k: None)
    resp = client.post(
        "/signup",
        json={
            "username": "Display Name",
            "email": "real.address@test.com",
            "password": "12345678",
        },
    )
    assert resp.status_code == 201, resp.text
    row = session.query(User).filter_by(email="real.address@test.com").first()
    assert row is not None, "user must be stored under body.email"
    assert row.username == "Display Name"
    # Gravatar must hash the email, not the display name.
    assert "gravatar" in row.avatar


def test_grades_keep_disciplines_without_a_teacher(session):
    session.add(Group(id=77, name="G77"))
    session.add(Student(id=77, first_name="No", last_name="Teacher", group_id=77))
    session.add(Discipline(id=77, name="Orphan subject", teacher_id=None))
    session.flush()
    session.add(Grade(id=77, grade=10, student_id=77, discipline_id=77))
    session.commit()

    rows = repo_grades.list_grades(None, 77, 50, 0, session)
    assert [g.id for g in rows] == [77], "teacher-less grade vanished from the list"
    assert repo_grades.get_all(None, 77, session) == 1, "count dropped it too"


def test_student_model_no_longer_accepts_contacts():
    assert "contacts" not in StudentModel.model_fields
    # Extra keys are ignored, not persisted — no silent data loss claim.
    m = StudentModel(
        first_name="Ab",
        last_name="Cd",
        dob="2010-01-01",
        group_id=1,
        contacts={"contact_type": "phone", "contact_value": "1"},
    )
    assert not hasattr(m, "contacts")


@pytest.mark.parametrize(
    "exc, expected",
    [
        (IntegrityError("INSERT INTO users ...", {}, Exception("dup key")), 409),
        (OperationalError("SELECT secret_table.col", {}, Exception("boom")), 500),
    ],
)
def test_get_db_maps_errors_without_leaking_sql(exc, expected):
    gen = get_db()
    next(gen)
    with pytest.raises(HTTPException) as err:
        gen.throw(exc)
    assert err.value.status_code == expected
    detail = str(err.value.detail)
    for leak in ("INSERT", "SELECT", "secret_table", "dup key", "boom"):
        assert leak not in detail, f"{leak!r} leaked into the response"


@pytest.fixture
def demoted_admin(session):
    email = "demoted@test.com"
    session.query(User).filter_by(email=email).delete()
    session.add(
        User(
            username=email,
            email=email,
            password=hash_handler.get_password_hash("secret123"),
            confirmed=True,
            roles=Role.admin,
        )
    )
    session.commit()
    invalidate_user_cache(email)
    return email


def test_refresh_reads_role_from_db_not_from_the_token_claim(
    client, session, demoted_admin
):
    from jose import jwt

    from src.conf.config import settings
    from src.services.auth import create_refresh_token

    token = create_refresh_token({"sub": demoted_admin, "role": "admin"})

    # Demote after the refresh token was minted.
    session.query(User).filter_by(email=demoted_admin).update({"roles": Role.user})
    session.commit()
    invalidate_user_cache(demoted_admin)

    resp = client.post("/refresh", json={"refresh_token": token})
    assert resp.status_code == 200, resp.text
    claims = jwt.decode(
        resp.json()["access_token"],
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    assert claims["role"] == "user", "stale admin claim survived the refresh"


def test_refresh_rejects_unconfirmed_user(client, session):
    email = "unconfirmed@test.com"
    session.query(User).filter_by(email=email).delete()
    session.add(
        User(
            username=email,
            email=email,
            password=hash_handler.get_password_hash("secret123"),
            confirmed=False,
        )
    )
    session.commit()

    from src.services.auth import create_refresh_token

    resp = client.post(
        "/refresh", json={"refresh_token": create_refresh_token({"sub": email})}
    )
    assert resp.status_code == 401
