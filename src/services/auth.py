import pickle
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.conf.config import settings
from src.database.db import get_db
from src.repository import users as repository_user
from src.services.cache import redis_client, user_cache_key

# auto_error=False so a missing Authorization header is not an instant 401 —
# we fall back to the browser-session cookie below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

USER_CACHE_TTL = 900  # seconds


class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)


hash_handler = Hash()


async def create_access_token(data: dict, expires_delta: Optional[float] = None):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + timedelta(seconds=expires_delta)
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"iat": now, "exp": expire, "scope": "access_token"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Accept the token from the Bearer header (API/Swagger) or, when absent,
    # from the browser-session cookie set at /login/web.
    if token is None:
        token = request.cookies.get("access_token")
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("scope") != "access_token":
            raise credentials_exception
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cache_key = user_cache_key(email)
    cached = redis_client.get(cache_key)
    if cached is None:
        user = await repository_user.get_user_by_email(email, db)
        if user is None:
            raise credentials_exception
        redis_client.set(cache_key, pickle.dumps(user))
        redis_client.expire(cache_key, USER_CACHE_TTL)
    else:
        user = pickle.loads(cached)

    return user


def decode_access_token_email(token: str) -> Optional[str]:
    """Return the email carried by a valid access token, or None.

    Used by the browser-session middleware: unlike ``get_current_user`` it
    never raises, so an absent/expired/tampered cookie simply means "not
    logged in" instead of a 401.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("scope") != "access_token":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_email_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)
    to_encode.update({"iat": now, "exp": expire, "scope": "email_token"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_email_from_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload["scope"] == "email_token":
            return payload["sub"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scope for token"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid token for email verification",
        )
