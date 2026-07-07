"""Route-level tests: role-based access control and CRUD happy paths.

Authentication is faked by overriding ``get_current_user`` (same trick as the
seed tests) so we exercise the real RBAC dependency without issuing tokens.
Redis is replaced with a tiny in-memory double so the cached student-detail
endpoint runs its full JSON serialize/deserialize round-trip against a real
PostgreSQL row.
"""

import pytest

from main import app
from src.database.models import Role, User
from src.services import seed as seed_service
from src.services.auth import get_current_user


def _user_with_role(role: Role) -> User:
    return User(
        id=1,
        username="tester",
        email="tester@test.com",
        password="x",
        confirmed=True,
        roles=role,
    )


def _login_as(role: Role) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user_with_role(role)


@pytest.fixture(autouse=True)
def _reset_auth_override():
    # get_db stays overridden (client fixture); only clear the auth override.
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="module")
def seeded(session):
    """Seed a small, reproducible dataset once for this module."""
    seed_service.seed_database(session, teachers=3, students=5, faker_seed=1)
    return session


@pytest.fixture
def fake_redis(monkeypatch):
    """In-memory stand-in for the module-level Redis client used by routes."""
    store: dict = {}

    class _FakeRedis:
        def get(self, key):
            return store.get(key)

        def set(self, key, value):
            store[key] = value

        def expire(self, key, ttl):
            return None

        def delete(self, key):
            store.pop(key, None)

    fake = _FakeRedis()
    monkeypatch.setattr("src.routes.students.redis_client", fake)
    return store


VALID_STUDENT = {
    "first_name": "New",
    "last_name": "Student",
    "dob": "2011-03-04",
    "group_id": 1,
}
VALID_TEACHER = {"first_name": "New", "last_name": "Teacher", "dob": "1985-06-07"}


# --------------------------------------------------------------------------- #
# Role-based access control                                                    #
# --------------------------------------------------------------------------- #
class TestRBAC:
    def test_create_student_forbidden_for_user(self, client, seeded):
        _login_as(Role.user)
        resp = client.post("/students/", json=VALID_STUDENT)
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == "Operation forbidden"

    def test_create_student_allowed_for_moderator(self, client, seeded):
        _login_as(Role.moderator)
        resp = client.post("/students/", json=VALID_STUDENT)
        assert resp.status_code == 201, resp.text
        assert resp.json()["full_name"] == "New Student"

    def test_delete_student_forbidden_for_moderator(self, client, seeded):
        # Deletion is admin-only, even though a moderator may create/update.
        _login_as(Role.moderator)
        resp = client.delete("/students/1")
        assert resp.status_code == 403, resp.text

    def test_delete_student_allowed_for_admin(self, client, seeded, fake_redis):
        # fake_redis: the delete handler busts the student cache on success.
        _login_as(Role.admin)
        resp = client.delete("/students/5")
        assert resp.status_code == 204, resp.text

    def test_create_teacher_forbidden_for_user(self, client, seeded):
        _login_as(Role.user)
        resp = client.post("/teachers/", json=VALID_TEACHER)
        assert resp.status_code == 403, resp.text

    def test_create_teacher_allowed_for_moderator(self, client, seeded):
        _login_as(Role.moderator)
        resp = client.post("/teachers/", json=VALID_TEACHER)
        assert resp.status_code == 201, resp.text
        assert resp.json()["full_name"] == "New Teacher"

    def test_delete_grade_forbidden_for_user(self, client, seeded):
        _login_as(Role.user)
        resp = client.delete("/grades/1")
        assert resp.status_code == 403, resp.text


# --------------------------------------------------------------------------- #
# Public pages and cached detail                                               #
# --------------------------------------------------------------------------- #
class TestStudentPages:
    def test_students_list_is_public(self, client, seeded):
        # No auth override installed → the list must still render.
        resp = client.get("/students/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_student_detail_json_cache_round_trip(self, client, seeded, fake_redis):
        # First hit: cache miss → DB row is serialized to JSON and stored.
        first = client.get("/students/2")
        assert first.status_code == 200
        assert any(key.startswith("student:2") for key in fake_redis)

        # Second hit: cache hit → JSON is deserialized back (no pickle involved).
        second = client.get("/students/2")
        assert second.status_code == 200
        assert second.text == first.text

    def test_missing_student_returns_404(self, client, seeded, fake_redis):
        resp = client.get("/students/9999")
        assert resp.status_code == 404


class TestAggregates:
    def test_avg_grade_total_matches_page_rows(self, seeded):
        # The lean COUNT(DISTINCT) used for pagination must equal the number of
        # grouped rows the page query returns over the same joins.
        from src.repository import students as repo_students

        total = repo_students.get_all_avg_grade(seeded)
        rows = repo_students.get_students_avg_grade(1000, 0, seeded)
        assert total > 0
        assert total == len(rows)
