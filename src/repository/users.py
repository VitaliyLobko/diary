from libgravatar import Gravatar
from sqlalchemy.orm import Session

from src.database.models import Role, User
from src.schemas.users import UserModel
from src.services.cache import invalidate_user_cache


def create_user(body: UserModel, password, db: Session):
    gavatar = Gravatar(body.username)

    new_user = User(
        username=body.username,
        email=body.username,
        password=password,
        avatar=gavatar.get_image(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_user_by_email(email, db: Session) -> User | None:
    user: User | None = db.query(User).filter_by(email=email).first()
    return user


def confirmed_email(email: str, db: Session) -> None:
    user = get_user_by_email(email, db)
    user.confirmed = True
    db.commit()
    # Bust the cached copy so the now-confirmed status is read on next request.
    invalidate_user_cache(email)


def update_user_role(email: str, role: Role, db: Session) -> User | None:
    user = get_user_by_email(email, db)
    if user is None:
        return None
    user.roles = role
    db.commit()
    db.refresh(user)
    # Bust the cached copy so the new role takes effect on the next request
    # instead of lingering behind the old one until the TTL expires.
    invalidate_user_cache(email)
    return user
