"""Unit tests for the config secret guard and email-token decoding.

These run without Docker/DB — they exercise pure functions and settings.
"""

import pytest
from fastapi import HTTPException
from jose import jwt
from pydantic import ValidationError

from src.conf.config import DEV_SECRET_KEY, Settings, settings
from src.services.auth import (
    create_access_token,
    create_email_token,
    create_refresh_token,
    decode_access_token_email,
    decode_refresh_token_email,
    get_email_from_token,
)


class TestProductionSecretGuard:
    def test_production_with_placeholder_secret_is_rejected(self):
        with pytest.raises(ValidationError):
            Settings(app_env="production", secret_key=DEV_SECRET_KEY)

    def test_production_with_real_secret_is_allowed(self):
        cfg = Settings(app_env="production", secret_key="a-strong-random-secret")
        assert cfg.app_env == "production"

    def test_development_keeps_placeholder_secret(self):
        cfg = Settings(app_env="development", secret_key=DEV_SECRET_KEY)
        assert cfg.secret_key == DEV_SECRET_KEY


class TestGetEmailFromToken:
    def test_valid_email_token_returns_subject(self):
        token = create_email_token({"sub": "user@test.com"})
        assert get_email_from_token(token) == "user@test.com"

    def test_token_without_scope_returns_401_not_500(self):
        # Regression: a valid token missing the "scope" claim used to raise a
        # bare KeyError (→ 500) instead of a handled 401.
        token = jwt.encode(
            {"sub": "user@test.com"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(HTTPException) as exc:
            get_email_from_token(token)
        assert exc.value.status_code == 401

    def test_wrong_scope_is_rejected(self):
        token = jwt.encode(
            {"sub": "user@test.com", "scope": "access_token"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with pytest.raises(HTTPException) as exc:
            get_email_from_token(token)
        assert exc.value.status_code == 401

    def test_garbage_token_is_unprocessable(self):
        with pytest.raises(HTTPException) as exc:
            get_email_from_token("not-a-jwt")
        assert exc.value.status_code == 422


class TestRefreshTokenScope:
    def test_refresh_token_decodes_back(self):
        token = create_refresh_token({"sub": "user@test.com"})
        assert decode_refresh_token_email(token) == "user@test.com"

    def test_access_token_is_rejected_as_refresh(self):
        # scope separation: an access token must not pass as a refresh token
        token = create_access_token({"sub": "user@test.com"})
        assert decode_refresh_token_email(token) is None

    def test_refresh_token_is_rejected_as_access(self):
        token = create_refresh_token({"sub": "user@test.com"})
        assert decode_access_token_email(token) is None

    def test_garbage_refresh_token_is_none(self):
        assert decode_refresh_token_email("not-a-jwt") is None
