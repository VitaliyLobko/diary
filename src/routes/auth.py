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

from src.conf.config import settings
from src.database.db import get_db
from src.repository import users as repository_user
from src.repository.users import get_user_by_email
from src.schemas.users import RequestEmail, TokenModel, UserModel, UserResponse
from src.services.auth import (
    create_access_token,
    get_email_from_token,
    hash_handler,
)
from src.services.email import send_email

router = APIRouter(tags=["auth"])


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new user.

    The client may submit either a JSON body or standard form data. When the
    request has a JSON content type we parse it directly; otherwise we fall
    back to reading `Request.form()` so that simple HTML forms work without
    JavaScript.  This keeps existing tests unchanged (they send JSON) while
    resolving the ``model_attributes_type`` error observed when a
    multipart/form-data payload reached the endpoint.
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )

    exist_user = await repository_user.get_user_by_email(body.username, db)
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )

    password_hash = hash_handler.get_password_hash(body.password)
    new_user = await repository_user.create_user(body, password_hash, db)
    background_tasks.add_task(
        send_email, new_user.email, new_user.username, str(request.base_url)
    )
    return new_user


@router.post("/login", response_model=TokenModel)
async def login(
    request: Request,
    body: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = await repository_user.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email"
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed"
        )
    if not hash_handler.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    access_token = await create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/web")
async def login_web(
    body: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Browser login: verify credentials, store the JWT in an HttpOnly cookie
    and redirect to the home page as a logged-in user.

    Kept separate from the JSON ``/login`` endpoint so API clients, Swagger and
    the test-suite are unaffected. On failure we redirect back to ``/`` with a
    ``login_error`` query param that the navbar renders as an alert.
    """
    user = await repository_user.get_user_by_email(body.username, db)
    if user is None:
        error = "Invalid email"
    elif not user.confirmed:
        error = "Email not confirmed"
    elif not hash_handler.verify_password(body.password, user.password):
        error = "Invalid password"
    else:
        error = None

    if error:
        return RedirectResponse(
            url=f"/?login_error={error}", status_code=status.HTTP_303_SEE_OTHER
        )

    access_token = await create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: Session = Depends(get_db)):
    email = get_email_from_token(token)
    user = await get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repository_user.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    user = await get_user_by_email(body.email, db)
    if user:
        if user.confirmed:
            return {"message": "Your email is already confirmed"}
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Check your email for confirmation."}
