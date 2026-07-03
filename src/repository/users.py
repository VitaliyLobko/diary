from libgravatar import Gravatar
from sqlalchemy.orm import Session

from src.database.models import User
from src.schemas.users import UserModel


async def create_user(body: UserModel, password, db: Session):
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


async def get_user_by_email(email, db: Session) -> User | None:
    user: User | None = db.query(User).filter_by(email=email).first()
    return user


async def confirmed_email(email: str, db: Session) -> None:
    user = await get_user_by_email(email, db)
    user.confirmed = True
    db.commit()
