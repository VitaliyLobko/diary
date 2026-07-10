import logging

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from src.conf.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    # Postgres (or a proxy in front of it) drops idle connections; without this
    # the first request after a quiet spell fails on a stale pooled connection.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Dependency
def get_db():
    """Yield a session, translating DB failures into meaningful status codes.

    Everything used to collapse into a 400 carrying ``str(err)``, which both
    mislabelled server faults as client errors and leaked table names, column
    names and SQL fragments to the caller. Now a constraint violation — the one
    failure the client can actually act on — becomes a 409, and anything else
    is a 500 with the detail confined to the logs.
    """
    db = SessionLocal()
    try:
        yield db
    except IntegrityError:
        db.rollback()
        logger.warning("Integrity error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request conflicts with the current state of the data",
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )
    finally:
        db.close()
