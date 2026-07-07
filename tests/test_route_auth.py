from unittest.mock import MagicMock

from main import app


def test_create_user(client, user, monkeypatch):
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("/signup", json=user)
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["email"] == user.get("email")


def test_repeat_create_user(client, user, monkeypatch):
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("/signup", json=user)
    assert response.status_code == 409, response.text
    payload = response.json()
    assert payload["detail"] == "Account already exists"


def test_create_user_with_form(client, user, monkeypatch):
    # use a different email to avoid conflict with the JSON-based registration
    form_email = f"form+{user.get('email')}"
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post(
        "/signup",
        data={"username": form_email, "password": user.get("password")},
    )
    # first attempt using form should succeed just like JSON
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["email"] == form_email


def test_short_password_validation(client, monkeypatch):
    # verify both JSON and form submissions are rejected with 422
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    short = {
        "username": "short@test.com",
        "email": "short@test.com",
        "password": "12345",
    }

    def check_error(resp):
        assert resp.status_code == 422, resp.text
        payload = resp.json()
        errors = payload.get("detail")
        assert isinstance(errors, list)
        assert any("password" in err.get("loc", []) for err in errors), (
            f"no password error in {errors}"
        )

    resp_json = client.post("/signup", json=short)
    check_error(resp_json)

    resp_form = client.post(
        "/signup",
        data={"username": short["email"], "password": short["password"]},
    )
    check_error(resp_form)


def test_login_is_rate_limited(client):
    # Re-enable the limiter locally (the suite disables it globally) and hammer
    # /login past its per-minute cap; excess requests must get 429.
    limiter = app.state.limiter
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post(
                "/login", data={"username": "nobody@test.com", "password": "wrong"}
            ).status_code
            for _ in range(12)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert 429 in codes


def test_request_email_resend(client, user, monkeypatch):
    # The user was created (and left unconfirmed) by an earlier test in this
    # module, so requesting a new confirmation email must trigger send_email.
    mock_send_email = MagicMock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)

    response = client.post("/request_email", json={"email": user["email"]})
    assert response.status_code == 200
    assert "Check your email" in response.json()["message"]
    mock_send_email.assert_called()


#
#
# def test_login_user_not_confirmed_email(client, user):
#     response = client.post(
#         "/auth/login",
#         data={"username": user.get("email"), "password": user.get("password")},
#     )
#     assert response.status_code == 401, response.text
#     payload = response.json()
#     assert payload["detail"] == "EMAIL NOT CONFIRMED"
#
#
# def test_login_user(client, user, session):
#     current_user: User = (
#         session.query(User).filter(User.email == user.get("email")).first()
#     )
#     current_user.confirmed = True
#     session.commit()
#     response = client.post(
#         "/auth/login",
#         data={"username": user.get("email"), "password": user.get("password")},
#     )
#     assert response.status_code == 200, response.text
#     payload = response.json()
#     assert payload["token_type"] == "bearer"
#
#
# def test_login_user_with_wrong_password(client, user, session):
#     current_user: User = (
#         session.query(User).filter(User.email == user.get("email")).first()
#     )
#     current_user.confirmed = True
#     session.commit()
#     response = client.post(
#         "/auth/login", data={"username": user.get("email"), "password": "password"}
#     )
#     assert response.status_code == 401, response.text
#     payload = response.json()
#     assert payload["detail"] == "Invalid password"
#
#
# def test_login_user_with_wrong_email(client, user, session):
#     current_user: User = (
#         session.query(User).filter(User.email == user.get("email")).first()
#     )
#     current_user.confirmed = True
#     session.commit()
#     response = client.post(
#         "/auth/login",
#         data={"username": "eaxample@test.com", "password": user.get("password")},
#     )
#     assert response.status_code == 401, response.text
#     payload = response.json()
#     assert payload["detail"] == "Invalid email"
