from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator, String
from datetime import datetime

engine = create_engine("sqlite:///telegram.db", connect_args={"autocommit": False})

class Base(DeclarativeBase):
    pass


class TimezoneAware(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None: return value
        return value.isoformat()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return datetime.fromisoformat(value)



import db.models

SessionLocal = sessionmaker(bind=engine)

def init_db(engine):
    Base.metadata.create_all(engine)

def get_session() -> Session:
    return SessionLocal()
