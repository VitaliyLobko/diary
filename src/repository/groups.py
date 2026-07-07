from sqlalchemy.orm import Session

from src.database.models import Group
from src.schemas.groups import GroupModel


def create_group(body: GroupModel, db: Session):
    group = Group(**body.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def get_all(db: Session):
    total_groups = db.query(Group).count()
    return total_groups


def get_groups(limit, offset, db: Session):
    groups = db.query(Group).order_by(Group.name).limit(limit).offset(offset).all()
    return groups


def update_group(body: GroupModel, group: Group, db: Session):
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(group, name, value)
    db.commit()
    return group


def delete_group(group, db: Session):
    db.delete(group)
    db.commit()
    return group
