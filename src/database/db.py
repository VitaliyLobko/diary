from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from src.conf.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as err:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    finally:
        db.close()
