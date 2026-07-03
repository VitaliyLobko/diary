import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.conf.config import settings
from src.services.auth import create_email_token

logger = logging.getLogger(__name__)


def _build_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_STARTTLS=False,
        MAIL_SSL_TLS=True,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=Path(__file__).parent.parent.parent / "templates",
    )


async def send_email(email: EmailStr, username: str, host: str):
    """Send a verification email.

    In development there is usually no real SMTP server configured, so the
    confirmation link is always logged. Delivery errors are non-fatal: the link
    stays visible in the logs so registration can still be tested locally.
    """
    token_verification = create_email_token({"sub": email})
    link = f"{host}confirmed_email/{token_verification}"
    logger.info("Verification link for %s: %s", email, link)

    try:
        message = MessageSchema(
            subject="Confirm your email",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(_build_config())
        await fm.send_message(message, template_name="email.html")
    except ConnectionErrors as err:
        logger.warning("Failed to send email (see link above): %s", err)
