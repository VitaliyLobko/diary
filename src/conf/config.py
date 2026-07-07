"""Application configuration.

All settings are read from environment variables (optionally from a local
``.env`` file) and fall back to safe development defaults, so the project can be
imported and the test-suite can run without any external services configured.
"""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Placeholder JWT key. Fine for local dev; refused in production (see validator).
DEV_SECRET_KEY = "dev-secret-change-me"


class Settings(BaseSettings):
    # Deployment environment: "development" (default) or "production". In
    # production the app refuses to start with insecure placeholder secrets.
    app_env: str = "development"

    # Database (PostgreSQL only; matches the docker-compose "db" service)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/sdiary"
    sqlalchemy_echo: bool = False

    # JWT authentication
    secret_key: str = DEV_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    # A longer-lived refresh token renews the short access token, so the browser
    # session doesn't drop every 15 minutes.
    refresh_token_expire_days: int = 7
    # Send the session cookie only over HTTPS. Off by default so local dev over
    # http:// still works; turn on in production (COOKIE_SECURE=true).
    cookie_secure: bool = False

    # Redis cache
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Outgoing mail
    mail_username: str = "school_diary@example.com"
    mail_password: str = ""
    mail_from: str = "school_diary@example.com"
    mail_port: int = 465
    mail_server: str = "smtp.example.com"
    mail_from_name: str = "School diary app"
    # Transport security — production defaults to SMTPS (SSL/TLS) with
    # credentials. Local dev SMTP catchers (MailHog/Mailpit) need these off.
    mail_starttls: bool = False
    mail_ssl_tls: bool = True
    mail_use_credentials: bool = True
    mail_validate_certs: bool = True

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _guard_production_secrets(self):
        # Fail loudly instead of silently signing JWTs with a publicly known
        # key. Only enforced in production so tests and local dev keep working.
        if self.app_env == "production" and self.secret_key == DEV_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value when "
                "APP_ENV=production (the development placeholder is refused)."
            )
        return self


settings = Settings()
