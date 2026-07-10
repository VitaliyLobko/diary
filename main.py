import pathlib
import time

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from src.conf.config import settings
from src.database.db import get_db
from src.routes import auth, seed
from src.routes.api.v1.api import router as api_v1_router
from src.routes.web import dashboard as web_dashboard
from src.routes.web import disciplines as web_disciplines
from src.routes.web import grades as web_grades
from src.routes.web import groups as web_groups
from src.routes.web import students as web_students
from src.routes.web import teachers as web_teachers
from src.services.auth import (
    create_access_token,
    decode_access_token_email,
    decode_access_token_role,
    decode_refresh_token_email,
    resolve_user_role,
)
from src.services.rate_limit import limiter

app = FastAPI()

# Rate limiting for the auth endpoints (see src/services/rate_limit.py).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # A wildcard origin cannot be combined with credentials, so keep it disabled.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    # A request-timing header is handy while developing but leaks internal
    # performance details, so keep it out of production responses.
    if settings.app_env != "production":
        response.headers["X-Process-Time"] = f"{time.time() - start_time:.4f}"
    return response


@app.middleware("http")
async def load_session_user(request: Request, call_next):
    # Expose the logged-in user's email to every template, and keep the session
    # alive by silently minting a fresh access token from the longer-lived
    # refresh cookie once the short one expires — no more logout every 15 min.
    access = request.cookies.get("access_token")
    email = decode_access_token_email(access) if access else None
    role = decode_access_token_role(access) if email else None
    valid_access = access if email else None

    if email is None:
        refresh = request.cookies.get("refresh_token")
        email = decode_refresh_token_email(refresh) if refresh else None
        if email:
            # The stored role, not the refresh token's frozen claim.
            role = resolve_user_role(email)
            valid_access = create_access_token({"sub": email, "role": role})

    request.state.user_email = email
    request.state.user_role = role
    request.state.access_token = valid_access

    response = await call_next(request)

    # A freshly minted token (different from the cookie) was refreshed from the
    # refresh cookie — persist it so the browser sends the current one next time.
    if valid_access and valid_access != access:
        response.set_cookie(
            "access_token",
            valid_access,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=settings.access_token_expire_minutes * 60,
        )
    return response


BASE_DIR = pathlib.Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# JSON API for programmatic clients (mobile app, etc.), versioned under /api/v1.
app.include_router(api_v1_router, prefix="/api/v1")

# Server-rendered site (Jinja). Each resource is a GET-only web router; its
# writes live in the JSON API mounted above.
app.include_router(web_dashboard.router)
app.include_router(web_students.router)
app.include_router(web_teachers.router)
app.include_router(web_groups.router)
app.include_router(web_disciplines.router)
app.include_router(web_grades.router)
app.include_router(seed.router)
app.include_router(auth.router)


@app.get("/healthchecker")
def healthchecker(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("Select 1")).fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="DB is not worked")
        return {"message": "Welcome to Students diary FastAPI"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to db - {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
