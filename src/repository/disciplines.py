from sqlalchemy.orm import Session

from src.database.models import Discipline, Teacher
from src.schemas.disciplines import DisciplineModel


async def create_discipline(body: DisciplineModel, db: Session):
    discipline = Discipline(**body.model_dump())
    db.add(discipline)
    db.commit()
    db.refresh(discipline)
    return discipline


async def get_all_dicsiplines(db):
    disciplines = db.query(Discipline).count()
    return disciplines


async def get_disciplines(limit, offset, db: Session):
    disciplines = (
        db.query(Discipline.id, Discipline.name, Teacher.id, Teacher.full_name)
        .join(Teacher)
        .order_by(Discipline.name)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return disciplines


async def update_discipline(body: DisciplineModel, discipine: int, db: Session):
    for name, value in body:
        setattr(discipine, name, value)
    db.commit()
    return discipine


async def delete_discipline(discipline, db: Session):
    db.delete(discipline)
    db.commit()
    return discipline
