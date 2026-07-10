from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import Role
from src.repository import users as repository_user
from src.repository.users import get_user_by_email
from src.schemas.users import (
    RequestEmail,
    RoleUpdate,
    TokenModel,
    UserModel,
    UserResponse,
)
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_access_token_email,
    decode_refresh_token_email,
    get_email_from_token,
    hash_handler,
)
from src.services.cache import invalidate_user_cache
from src.services.email import send_email
from src.services.rate_limit import (
    EMAIL_LIMIT,
    LOGIN_LIMIT,
    REFRESH_LIMIT,
    SIGNUP_LIMIT,
    limiter,
)
from src.services.roles import RoleAccess

router = APIRouter(tags=["auth"])

allowed_manage_roles = RoleAccess([Role.admin])

# Shown for both "no such email" and "wrong password" so the response never
# reveals which accounts exist (user enumeration).
INVALID_CREDENTIALS = "Invalid email or password"


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(SIGNUP_LIMIT)
async def signup(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new user.

    Stays ``async`` because it inspects the raw request body: the client may
    submit either a JSON body or standard form data. When the request has a
    JSON content type we parse it directly; otherwise we fall back to reading
    ``Request.form()`` so that simple HTML forms work without JavaScript. This
    keeps existing tests unchanged (they send JSON) while resolving the
    ``model_attributes_type`` error observed when a multipart/form-data payload
    reached the endpoint.

    Because the handler is ``async`` it runs *on* the event loop, so the two
    genuinely blocking steps — the bcrypt hash (~100 ms of pure CPU) and the
    synchronous DB calls — are pushed to the threadpool. Left inline they stall
    every other in-flight request for the duration.
    """
    # determine how the data was sent
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = {"username": form.get("username"), "password": form.get("password")}
        # HTML form only includes a single "username" field that holds the
        # user's email address.  The Pydantic model requires a separate
        # `email` field, so mirror it here when missing.
        if "email" not in data or not data.get("email"):
            data["email"] = data.get("username")

    # Validate and convert; surface validation errors as 422 instead of 500.
    try:
        body = UserModel(**data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        )

    # Look up by the column ``create_user`` actually writes — ``email``.
    exist_user = await run_in_threadpool(get_user_by_email, body.email, db)
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )

    password_hash = await run_in_threadpool(
        hash_handler.get_password_hash, body.password
    )
    new_user = await run_in_threadpool(
        repository_user.create_user, body, password_hash, db
    )
    background_tasks.add_task(
        send_email, new_user.email, new_user.username, str(request.base_url)
    )
    return new_user


@router.post("/login", response_model=TokenModel)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    body: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(body.username, db)
    # Verify credentials before saying anything specific: a missing user and a
    # wrong password give the same generic error, so neither confirms whether
    # an email is registered. "Not confirmed" is only revealed to someone who
    # already proved they own the account.
    if user is None or not hash_handler.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed"
        )
    role = user.roles.value if user.roles is not None else None
    access_token = create_access_token(data={"sub": user.email, "role": role})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": role})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login/web")
@limiter.limit(LOGIN_LIMIT)
def login_web(
    request: Request,
    body: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Browser login: verify credentials, store the JWT in an HttpOnly cookie
    and redirect to the home page as a logged-in user.

    Kept separate from the JSON ``/login`` endpoint so API clients, Swagger and
    the test-suite are unaffected. On failure we redirect back to ``/`` with a
    ``login_error`` query param that the navbar renders as an alert.
    """
    user = get_user_by_email(body.username, db)
    if user is None or not hash_handler.verify_password(body.password, user.password):
        error = INVALID_CREDENTIALS
    elif not user.confirmed:
        error = "Email not confirmed"
    else:
        error = None

    if error:
        return RedirectResponse(
            url=f"/?login_error={error}", status_code=status.HTTP_303_SEE_OTHER
        )

    role = user.roles.value if user.roles is not None else None
    access_token = create_access_token(data={"sub": user.email, "role": role})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": role})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return response


@router.post("/refresh", response_model=TokenModel)
@limiter.limit(REFRESH_LIMIT)
async def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a fresh access (and refresh) token.

    The refresh token is read from the ``refresh_token`` cookie (browser) or a
    JSON body ``{"refresh_token": "..."}`` (API clients). Browsers normally
    don't need this endpoint — the session middleware refreshes transparently.

    ``async`` (it may await the request body), so the DB lookup is offloaded
    rather than blocking the event loop.
    """
    token = request.cookies.get("refresh_token")
    if token is None:
        try:
            data = await request.json()
        except Exception:
            data = {}
        token = data.get("refresh_token") if isinstance(data, dict) else None

    email = decode_refresh_token_email(token) if token else None
    user = await run_in_threadpool(get_user_by_email, email, db) if email else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    # An account disabled after the refresh token was issued must not be able to
    # mint fresh credentials from it — /login already refuses these users.
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed"
        )

    # Read the role from the DB, not from the refresh token's claim: a demoted
    # admin would otherwise keep minting admin-claimed access tokens for the
    # remaining lifetime of the refresh token (up to 7 days).
    role = user.roles.value if user.roles is not None else None
    return {
        "access_token": create_access_token(data={"sub": email, "role": role}),
        "refresh_token": create_refresh_token(data={"sub": email, "role": role}),
        "token_type": "bearer",
    }


@router.get("/logout")
def logout(request: Request):
    # Drop the user's cached record on the way out, so a later change to their
    # role/status can't be masked by a stale cache entry after they log back in.
    token = request.cookies.get("access_token")
    if token:
        email = decode_access_token_email(token)
        if email:
            invalidate_user_cache(email)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


@router.put(
    "/users/{email}/role",
    response_model=UserResponse,
    dependencies=[Depends(allowed_manage_roles)],
)
def set_user_role(
    email: str,
    body: RoleUpdate,
    db: Session = Depends(get_db),
):
    """Assign a role to a user (admin only).

    Updates the DB and invalidates the user's cached record so the new role
    takes effect immediately, instead of editing the ``roles`` column by hand.
    """
    user = repository_user.update_user_role(email, body.role, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/confirmed_email/{token}")
def confirmed_email(token: str, db: Session = Depends(get_db)):
    email = get_email_from_token(token)
    user = get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    repository_user.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post("/request_email")
@limiter.limit(EMAIL_LIMIT)
def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(body.email, db)
    if user:
        if user.confirmed:
            return {"message": "Your email is already confirmed"}
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Check your email for confirmation."}
