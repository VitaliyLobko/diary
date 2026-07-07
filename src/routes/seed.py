from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Role
from src.services import seed as seed_service
from src.services.roles import RoleAccess

router = APIRouter(prefix="/seed", tags=["seed"])

allowed_operation_create = RoleAccess([Role.admin])


@router.post("/", dependencies=[Depends(allowed_operation_create)])
def seed(
    reset: bool = False,
    teachers: int = seed_service.DEFAULT_TEACHERS,
    students: int = seed_service.DEFAULT_STUDENTS,
    faker_seed: int | None = None,
    db: Session = Depends(get_db),
):
    """Populate the database with demo data (admin only).

    Exposed as POST because it mutates — and with ``?reset=true`` destroys —
    data, so it must never be reachable by a plain GET (link preview, prefetch,
    crawler). Idempotent by default: if data already exists the request is a
    no-op unless ``reset=true`` is passed. ``teachers``/``students`` size the
    dataset; ``faker_seed`` makes the generated data reproducible.
    """
    existing = seed_service.student_count(db)
    if existing and not reset:
        return {
            "status": "skipped",
            "reason": "database already contains data; pass ?reset=true to reseed",
            "students": existing,
        }

    result = seed_service.seed_database(
        db,
        teachers=teachers,
        students=students,
        reset=reset,
        faker_seed=faker_seed,
    )
    return {"status": "reseeded" if reset else "seeded", "counts": result}
