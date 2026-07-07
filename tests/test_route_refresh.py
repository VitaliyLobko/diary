"""Integration tests for the refresh-token flow.

Covers the /refresh endpoint and the session middleware that silently mints a
new access token from the refresh cookie.
"""

import pytest

from src.database.models import User
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    hash_handler,
)


@pytest.fixture
def stored_email(session):
    email = "refresh@test.com"
    if session.query(User).filter_by(email=email).first() is None:
        session.add(
            User(
                username=email,
                email=email,
                password=hash_handler.get_password_hash("secret123"),
                confirmed=True,
            )
        )
        session.commit()
    return email


@pytest.fixture(autouse=True)
def _clean_cookies(client):
    # Start each test with an empty cookie jar so the explicit Cookie header is
    # the only cookie in play.
    client.cookies.clear()
    yield


def _cookie(name, value):
    return {"Cookie": f"{name}={value}"}


def test_refresh_returns_new_tokens_from_cookie(client, stored_email):
    token = create_refresh_token({"sub": stored_email})
    resp = client.post("/refresh", headers=_cookie("refresh_token", token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_refresh_accepts_json_body(client, stored_email):
    token = create_refresh_token({"sub": stored_email})
    resp = client.post("/refresh", json={"refresh_token": token})
    assert resp.status_code == 200, resp.text


def test_refresh_rejects_access_token(client, stored_email):
    # an access token has the wrong scope and must not refresh
    token = create_access_token({"sub": stored_email})
    resp = client.post("/refresh", headers=_cookie("refresh_token", token))
    assert resp.status_code == 401


def test_refresh_rejects_unknown_user(client):
    token = create_refresh_token({"sub": "ghost@test.com"})
    resp = client.post("/refresh", headers=_cookie("refresh_token", token))
    assert resp.status_code == 401


def test_middleware_slides_session_from_refresh_cookie(client, stored_email):
    # No access cookie, only a valid refresh cookie: the middleware should mint
    # a fresh access token and set it on the response.
    token = create_refresh_token({"sub": stored_email})
    resp = client.get("/", headers=_cookie("refresh_token", token))
    assert resp.status_code == 200
    assert "access_token" in resp.cookies
