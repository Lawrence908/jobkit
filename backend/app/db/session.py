"""SQLAlchemy engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import Artifact, GoogleToken, Job


def get_engine():
    settings = get_settings()
    url = f"sqlite:///{settings.db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    return engine


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)


SessionLocal = None


def get_session_factory(engine):
    global SessionLocal
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def get_db():
    if SessionLocal is None:
        raise RuntimeError("DB not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
