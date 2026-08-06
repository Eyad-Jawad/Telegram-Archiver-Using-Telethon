from unittest.mock import MagicMock
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import db


@pytest.fixture
def mock_session():
    engine = create_engine("sqlite:///:memory:")

    db.init_db(engine)

    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()

@pytest.fixture
def mock_conn_and_cursor():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    return conn, cursor
