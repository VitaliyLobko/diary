from sqlalchemy.orm import Session

from src.database.models import Discipline, Teacher
from src.schemas.disciplines import DisciplineModel


def create_discipline(body: DisciplineModel, db: Session):
    teacher = db.query(Teacher).filter_by(id=body.teacher_id).first()
    if teacher is None:
        return None
    discipline = Discipline(**body.model_dump())
    db.add(discipline)
    db.commit()
    db.refresh(discipline)
    return discipline


def get_all_disciplines(db):
    disciplines = db.query(Discipline).count()
    return disciplines


def get_disciplines(limit, offset, db: Session):
    disciplines = (
        db.query(Discipline.id, Discipline.name, Teacher.id, Teacher.full_name)
        .outerjoin(Teacher)
        .order_by(Discipline.name)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return disciplines


def list_disciplines(limit, offset, db: Session):
    """Disciplines as ORM rows for the JSON API.

    ``get_disciplines`` returns a display Row that carries the teacher's name;
    the API instead wants full ``Discipline`` objects (with ``teacher_id``) that
    map onto ``DisciplineResponse``.
    """
    return (
        db.query(Discipline).order_by(Discipline.name).limit(limit).offset(offset).all()
    )


def update_discipline(body: DisciplineModel, discipline: int, db: Session):
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(discipline, name, value)
    db.commit()
    return discipline


def delete_discipline(discipline, db: Session):
    db.delete(discipline)
    db.commit()
    return discipline
