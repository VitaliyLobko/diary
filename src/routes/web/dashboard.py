"""Server-rendered home dashboard (Jinja). JSON counterpart:
``src/routes/api/v1/dashboard.py``.

Owns ``/`` — a summary of the whole school (counts, averages, grade
distribution, per-discipline/-group breakdowns, top students, recent grades)
built from the read-only aggregations in ``src/repository/dashboard.py``.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import dashboard as repository_dashboard

router = APIRouter(tags=["web:dashboard"], default_response_class=HTMLResponse)
templates = Jinja2Templates(directory="templates")


@router.get("/", name="Home dashboard page")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    data = repository_dashboard.get_dashboard(db)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "title": "Dashboard", **data},
    )
