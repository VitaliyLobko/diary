import pathlib
import time

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from src.database.db import get_db
from src.routes import auth, disciplines, grades, groups, seed, students, teachers

app = FastAPI()


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
    during = time.time() - start_time
    response.headers["performance"] = str(during)
    return response


BASE_DIR = pathlib.Path(__file__).parent

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(groups.router)
app.include_router(disciplines.router)
app.include_router(grades.router)
app.include_router(seed.router)
app.include_router(auth.router)


@app.get("/healthchecker")
async def healthchecker(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("Select 1")).fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="DB is not worked")
        return {"message": "Welcome to Students diary FastAPI"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to db - {e}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "title": "Home App"}
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
