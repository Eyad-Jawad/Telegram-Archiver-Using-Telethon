from datetime import datetime

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import String, TypeDecorator

engine = create_async_engine(
    "sqlite+aiosqlite:///telegram.db", connect_args={"autocommit": False}
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


SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db(engine):
    from . import models as models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    return SessionLocal()
