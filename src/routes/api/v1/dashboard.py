"""Dashboard JSON API (mounted under ``/api/v1``).

A single read-only endpoint returning the same summary statistics the Jinja home
page renders (``src/routes/web/dashboard.py``), for the planned mobile app.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.repository import dashboard as repository_dashboard
from src.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["api:dashboard"])


@router.get(
    "/",
    response_model=DashboardResponse,
    name="Get dashboard summary",
)
def get_dashboard(db: Session = Depends(get_db)):
    return repository_dashboard.get_dashboard(db)
