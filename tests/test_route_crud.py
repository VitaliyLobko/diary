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

        def setex(self, key, ttl, value):
            store[key] = value

        def delete(self, key):
            store.pop(key, None)

    # Every reader and writer goes through the cache_* helpers, which resolve
    # ``redis_client`` off this module at call time — one patch covers them all.
    monkeypatch.setattr("src.services.cache.redis_client", _FakeRedis())
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
        resp = client.post("/api/v1/students/", json=VALID_STUDENT)
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == "Operation forbidden"

    def test_create_student_allowed_for_moderator(self, client, seeded):
        _login_as(Role.moderator)
        resp = client.post("/api/v1/students/", json=VALID_STUDENT)
        assert resp.status_code == 201, resp.text
        assert resp.json()["full_name"] == "New Student"

    def test_delete_student_forbidden_for_moderator(self, client, seeded):
        # Deletion is admin-only, even though a moderator may create/update.
        _login_as(Role.moderator)
        resp = client.delete("/api/v1/students/1")
        assert resp.status_code == 403, resp.text

    def test_delete_student_allowed_for_admin(self, client, seeded, fake_redis):
        # fake_redis: the delete handler busts the student cache on success.
        _login_as(Role.admin)
        resp = client.delete("/api/v1/students/5")
        assert resp.status_code == 204, resp.text

    def test_create_teacher_forbidden_for_user(self, client, seeded):
        _login_as(Role.user)
        resp = client.post("/api/v1/teachers/", json=VALID_TEACHER)
        assert resp.status_code == 403, resp.text

    def test_create_teacher_allowed_for_moderator(self, client, seeded):
        _login_as(Role.moderator)
        resp = client.post("/api/v1/teachers/", json=VALID_TEACHER)
        assert resp.status_code == 201, resp.text
        assert resp.json()["full_name"] == "New Teacher"

    def test_delete_grade_forbidden_for_user(self, client, seeded):
        _login_as(Role.user)
        resp = client.delete("/api/v1/grades/1")
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


class TestJsonApi:
    """The /api/v1 surface returns JSON (not HTML) and its response models
    serialize the ORM/Row objects the repository hands back."""

    def test_students_api_is_json_web_is_html(self, client, seeded):
        api = client.get("/api/v1/students/")
        web = client.get("/students/")
        assert "application/json" in api.headers["content-type"]
        assert "text/html" in web.headers["content-type"]

    def test_teachers_list_and_detail(self, client, seeded):
        rows = client.get("/api/v1/teachers/").json()
        assert rows and {"id", "full_name", "dob", "is_active"} <= rows[0].keys()
        detail = client.get(f"/api/v1/teachers/{rows[0]['id']}")
        assert detail.status_code == 200
        # detail carries the split name/photo the list view omits
        assert {"first_name", "last_name", "photo"} <= detail.json().keys()

    def test_groups_list_json(self, client, seeded):
        rows = client.get("/api/v1/groups/").json()
        assert rows and {"id", "name"} <= rows[0].keys()

    def test_disciplines_list_json(self, client, seeded):
        rows = client.get("/api/v1/disciplines/").json()
        assert rows and {"id", "name", "teacher_id"} <= rows[0].keys()

    def test_grades_list_json(self, client, seeded):
        rows = client.get("/api/v1/grades/").json()
        assert rows
        assert {"id", "grade", "date_of", "student_id", "discipline_id"} <= rows[
            0
        ].keys()


class TestWebPagesRender:
    """Every server-rendered page must return 200 HTML. A template that
    references a field the row doesn't carry only fails at render time — a 500
    when a human opens the page, invisible to the JSON API tests — so smoke-test
    that each page renders."""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/students/",
            "/students/avg_grade",
            "/students/top_10_students",
            "/teachers/",
            "/groups/",
            "/disciplines/",
            "/grades/",
        ],
    )
    def test_list_page_renders(self, client, seeded, path):
        resp = client.get(path)
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_student_detail_page_renders(self, client, seeded, fake_redis):
        # fake_redis: the detail page reads/writes the student cache.
        sid = client.get("/api/v1/students/").json()[0]["id"]
        resp = client.get(f"/students/{sid}")
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_teacher_detail_page_renders(self, client, seeded):
        tid = client.get("/api/v1/teachers/").json()[0]["id"]
        resp = client.get(f"/teachers/{tid}")
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_discipline_detail_page_renders(self, client, seeded):
        did = client.get("/api/v1/disciplines/").json()[0]["id"]
        resp = client.get(f"/disciplines/{did}")
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_grade_detail_page_renders(self, client, seeded):
        gid = client.get("/api/v1/grades/").json()[0]["id"]
        resp = client.get(f"/grades/{gid}")
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]

    def test_group_detail_page_renders(self, client, seeded):
        gid = client.get("/api/v1/groups/").json()[0]["id"]
        resp = client.get(f"/groups/{gid}")
        assert resp.status_code == 200, resp.text
        assert "text/html" in resp.headers["content-type"]


class TestPaginationBounds:
    def test_limit_below_one_is_rejected(self, client, seeded):
        assert client.get("/students/?limit=0").status_code == 422

    def test_limit_above_max_is_rejected(self, client, seeded):
        assert client.get("/students/?limit=999").status_code == 422

    def test_negative_offset_is_rejected(self, client, seeded):
        assert client.get("/students/?offset=-1").status_code == 422

    def test_defaults_are_accepted(self, client, seeded):
        assert client.get("/students/").status_code == 200


class TestGradeFilters:
    def test_empty_discipline_filter_is_ok(self, client, seeded):
        # The "all disciplines" option submits discipline= (empty string); it
        # must be treated as "no filter", not rejected as an invalid int.
        assert client.get("/grades/?discipline=").status_code == 200

    def test_numeric_discipline_filter_is_ok(self, client, seeded):
        assert client.get("/grades/?discipline=1").status_code == 200


class TestPhotoRoutes:
    def test_upload_then_delete_student_photo(
        self, client, seeded, fake_redis, monkeypatch, tmp_path
    ):
        monkeypatch.setattr("src.services.uploads.UPLOAD_DIR", tmp_path)
        _login_as(Role.moderator)

        resp = client.post(
            "/api/v1/students/1/photo",
            files={"file": ("p.jpg", b"\xff\xd8imagebytes", "image/jpeg")},
        )
        assert resp.status_code == 200, resp.text
        name = resp.json()["photo"]
        assert name and (tmp_path / name).exists()

        resp = client.delete("/api/v1/students/1/photo")
        assert resp.status_code == 200
        assert resp.json()["photo"] is None
        assert not (tmp_path / name).exists()

    def test_upload_rejects_non_image(
        self, client, seeded, fake_redis, monkeypatch, tmp_path
    ):
        monkeypatch.setattr("src.services.uploads.UPLOAD_DIR", tmp_path)
        _login_as(Role.moderator)
        resp = client.post(
            "/api/v1/students/1/photo",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400


class TestAggregates:
    def test_students_total_respects_search(self, seeded):
        from src.repository import students as repo

        unfiltered = repo.get_all("", seeded)
        everyone = repo.get_students("", unfiltered + 10, 0, seeded)
        name = everyone[0].first_name

        filtered_rows = repo.get_students(name, unfiltered + 10, 0, seeded)
        filtered_total = repo.get_all(name, seeded)

        # The total used for pagination must match the filtered page rows and
        # never exceed the unfiltered count.
        assert filtered_total == len(filtered_rows)
        assert filtered_total <= unfiltered

    def test_teachers_total_respects_search(self, seeded):
        from src.repository import teachers as repo

        unfiltered = repo.get_all("", seeded)
        everyone = repo.get_teachers("", unfiltered + 10, 0, seeded)
        name = everyone[0].first_name

        filtered_rows = repo.get_teachers(name, unfiltered + 10, 0, seeded)
        filtered_total = repo.get_all(name, seeded)

        assert filtered_total == len(filtered_rows)
        assert filtered_total <= unfiltered
        # the filter actually narrows: every hit contains the search term
        assert all(name.lower() in t.full_name.lower() for t in filtered_rows)

    def test_avg_grade_total_matches_page_rows(self, seeded):
        # The lean COUNT(DISTINCT) used for pagination must equal the number of
        # grouped rows the page query returns over the same joins.
        from src.repository import students as repo_students

        total = repo_students.get_all_avg_grade(seeded)
        rows = repo_students.get_students_avg_grade(1000, 0, seeded)
        assert total > 0
        assert total == len(rows)
