"""Application configuration.

All settings are read from environment variables (optionally from a local
``.env`` file) and fall back to safe development defaults, so the project can be
imported and the test-suite can run without any external services configured.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./school_diary.db"
    sqlalchemy_echo: bool = False

    # JWT authentication
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

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


settings = Settings()
