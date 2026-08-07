from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import db


@pytest_asyncio.fixture
async def mock_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"autocommit": False}, echo=False,
    )

    await db.init_db(engine)

    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    session = SessionLocal()

    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.fixture
def mock_conn_and_cursor():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    return conn, cursor
