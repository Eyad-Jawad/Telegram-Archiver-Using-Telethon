from unittest.mock import MagicMock

import pytest, pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

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
