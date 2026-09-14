from unittest.mock import MagicMock
from datetime import datetime, UTC

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import db
from db.models import Message, Dialog


@pytest_asyncio.fixture
async def mock_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
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


@pytest.fixture
def mock_message() -> Message:
    msg = Message()

    return msg


@pytest.fixture
def check_db_msg_defaults(mock_session):
    async def _check_db_msg_defaults(msg: Message, *, skips=()):
        dialog = Dialog()
        dialog.dialog_id = 1
        dialog.name = "1"
        dialog.type = "Something"

        msg.message_id = 1
        msg.dialog_id = 1
        msg.date = datetime.now(UTC)

        mock_session.add(dialog)
        mock_session.add(msg)
        await mock_session.commit()

        if "author_name" not in skips:
            assert msg.author_name == ""

        if "views" not in skips:
            assert msg.views == 1

        if "sender_id" not in skips:
            assert msg.sender_id == 0

        if "forward_from_username" not in skips:
            assert msg.forward_from_username == ""

        if "forward_from_user_id" not in skips:
            assert msg.forward_from_user_id == 0

        if "replied_to_id" not in skips:
            assert msg.replied_to_id == 0

        if "replied_to_entity_id" not in skips:
            assert msg.replied_to_entity_id == 0

        if "replied_to_text" not in skips:
            assert msg.replied_to_text == ""

        if "text" not in skips:
            assert msg.text == ""

        if "file_path" not in skips:
            assert msg.file_path == ""

        if "file_name" not in skips:
            assert msg.file_name == ""

        if "file_id" not in skips:
            assert msg.file_id == ""

        if "file_size" not in skips:
            assert msg.file_size == 0.0

        if "downloaded_file" not in skips:
            assert msg.downloaded_file == False

    return _check_db_msg_defaults
