import pytest

from main import app
from src.database.models import Role, User
from src.services.auth import get_current_user

# The disciplines/groups lists are fixed, so their seeded counts are constant.
from src.services.seed import DISCIPLINES, GROUP_NAMES


def _as(role):
    """Dependency override that authenticates every request as `role`."""

    def _dep():
        return User(
            id=1,
            username="admin",
            email="admin@test.com",
            password="x",
            confirmed=True,
            roles=role,
        )

    return _dep


@pytest.fixture
def as_admin():
    app.dependency_overrides[get_current_user] = _as(Role.admin)
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_user():
    app.dependency_overrides[get_current_user] = _as(Role.user)
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_seed_requires_authentication(client):
    # No auth override → get_current_user runs for real, finds no cookie → 401.
    resp = client.post("/seed/")
    assert resp.status_code == 401, resp.text


def test_seed_forbidden_for_non_admin(client, as_user):
    resp = client.post("/seed/")
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "Operation forbidden"


def test_seed_rejects_get(client, as_admin):
    # Seeding is a mutation: it must not be reachable via GET.
    resp = client.get("/seed/")
    assert resp.status_code == 405, resp.text


def test_seed_populates(client, as_admin):
    resp = client.post(
        "/seed/", params={"teachers": 3, "students": 5, "faker_seed": 1}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "seeded"
    counts = body["counts"]
    assert counts["teachers"] == 3
    assert counts["students"] == 5
    assert counts["groups"] == len(GROUP_NAMES)
    assert counts["disciplines"] == len(DISCIPLINES)
    # one email + one mobile per person
    assert counts["contacts"] == (3 + 5) * 2
    assert counts["grades"] > 0


def test_seed_skips_when_data_exists(client, as_admin):
    resp = client.post("/seed/")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "skipped"
    assert body["students"] == 5


def test_seed_reset_reseeds_without_duplication(client, as_admin):
    resp = client.post(
        "/seed/",
        params={"reset": True, "teachers": 3, "students": 5, "faker_seed": 1},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "reseeded"
    counts = body["counts"]
    # counts back to the requested sizes — the wipe cleared the previous run
    assert counts["teachers"] == 3
    assert counts["students"] == 5
    assert counts["contacts"] == (3 + 5) * 2
