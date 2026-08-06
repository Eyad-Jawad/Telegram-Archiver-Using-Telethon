from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import String, TypeDecorator

engine = create_engine(
    "sqlite:///telegram.db", connect_args={"autocommit": False}
)


class Base(DeclarativeBase):
    pass


class TimezoneAware(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return value.isoformat()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return datetime.fromisoformat(value)


SessionLocal = sessionmaker(bind=engine)


def init_db(engine):
    from . import models as models

    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
