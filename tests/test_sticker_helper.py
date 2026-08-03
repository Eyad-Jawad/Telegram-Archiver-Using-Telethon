import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon import errors

from helpers.stickers import *


@pytest.fixture
def mock_cursor():
    conn = sqlite3.connect(":memory:")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sticker_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            message_id INTEGER,
            pack_name TEXT,
            pack_link TEXT,
            sticker_set_id INTEGER,
            access_hash INTEGER,
            UNIQUE (dialog_id, message_id)
        )
    """)

    yield cursor

    conn.close()


@pytest.fixture
def mock_message():
    message = MagicMock()
    message.id = 10
    sticker_set = MagicMock()
    sticker_set.id = 123
    sticker_set.access_hash = 321
    message.file = MagicMock()
    message.file.sticker_set = sticker_set

    return message


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_no_message(
    mock_get_info, mock_insert, mock_find
):
    await stickers_handler(None, None, None, None)

    mock_get_info.assert_not_awaited()
    mock_insert.assert_not_called()
    mock_find.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_no_file(
    mock_get_info, mock_insert, mock_find
):
    message = MagicMock()
    message.file = None
    await stickers_handler(None, message, None, None)

    mock_get_info.assert_not_awaited()
    mock_insert.assert_not_called()
    mock_find.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_no_sticker_set(
    mock_get_info, mock_insert, mock_find
):
    message = MagicMock()
    message.file = MagicMock()
    message.file.sticker_set = None
    await stickers_handler(None, message, None, None)

    mock_get_info.assert_not_awaited()
    mock_insert.assert_not_called()
    mock_find.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_existing_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_cursor
):
    client = MagicMock()
    dialog_id = 1
    mock_find.return_value = ("pack", "link", 123, 321)
    await stickers_handler(client, mock_message, dialog_id, mock_cursor)

    mock_find.assert_called_once_with(mock_cursor, 123, 321)
    mock_insert.assert_called_once_with(
        mock_cursor, (1, 10, "pack", "link", 123, 321)
    )
    mock_get_info.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_new_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_cursor
):
    client = MagicMock()
    dialog_id = 1
    mock_find.return_value = None
    mock_get_info.return_value = ("things", "add", 123, 321)
    await stickers_handler(client, mock_message, dialog_id, mock_cursor)

    mock_find.assert_called_once_with(mock_cursor, 123, 321)
    mock_insert.assert_called_once_with(
        mock_cursor, (1, 10, "things", "add", 123, 321)
    )
    mock_get_info.assert_awaited_once_with(
        client, mock_message.file.sticker_set
    )


def test_insert_sticker_set_info_with_no_entry(mock_cursor):
    insert_sticker_set_info(mock_cursor, None)

    mock_cursor.execute("SELECT * FROM sticker_sets")

    assert [] == mock_cursor.fetchall()


def test_insert_sticker_set_info_with_one_entry(mock_cursor):
    insert_sticker_set_info(mock_cursor, (1, 10, "pack", "add", 123, 321))

    mock_cursor.execute("SELECT * FROM sticker_sets")

    assert [(1, 1, 10, "pack", "add", 123, 321)] == mock_cursor.fetchall()


def test_insert_sticker_set_info_with_many_entries(mock_cursor):
    insert_sticker_set_info(mock_cursor, (1, 10, "pack", "add", 123, 321))

    mock_cursor.execute("SELECT * FROM sticker_sets")

    assert [(1, 1, 10, "pack", "add", 123, 321)] == mock_cursor.fetchall()

    insert_sticker_set_info(mock_cursor, (1, 10, "names", "nah", 654, 456))

    assert [] == mock_cursor.fetchall()


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetStickerSetRequest")
async def test_get_sticker_set_info_with_valid_sticker_set(
    mock_requset, mock_message
):
    client = AsyncMock()
    result = MagicMock()
    result.title = "Pack"
    result.short_name = "add"
    mock_requset.return_value = "called"

    client.return_value = result

    sticker_set = mock_message.file.sticker_set
    assert await get_sticker_set_info(client, sticker_set) == (
        "Pack",
        "https://t.me/addstickers/add",
        123,
        321,
    )

    client.assert_awaited_once_with("called")
    mock_requset.assert_called_once_with(stickerset=sticker_set, hash=0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        errors.EmoticonStickerpackMissingError,
        errors.rpcerrorlist.StickersetInvalidError,
    ],
)
@patch("telethon.functions.messages.GetStickerSetRequest")
async def test_get_sticker_set_info_with_known_exceptions(
    mock_requset, error, mock_message
):
    client = AsyncMock(side_effect=error(None))
    mock_requset.return_value = "called"

    sticker_set = mock_message.file.sticker_set
    assert await get_sticker_set_info(client, sticker_set) == (
        "",
        "Pack is unavailable",
        123,
        321,
    )

    client.assert_awaited_once_with("called")
    mock_requset.assert_called_once_with(stickerset=sticker_set, hash=0)


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetStickerSetRequest")
async def test_get_sticker_set_info_with_unknown_exception(
    mock_requset, mock_message
):
    client = AsyncMock(side_effect=RuntimeError("Error"))
    mock_requset.return_value = "called"

    sticker_set = mock_message.file.sticker_set
    assert await get_sticker_set_info(client, sticker_set) == ("", "", 123, 321)

    client.assert_awaited_once_with("called")
    mock_requset.assert_called_once_with(stickerset=sticker_set, hash=0)


def test_find_sticker_set_in_db_with_empty_db(mock_cursor):
    assert find_sticker_set_in_db(mock_cursor, 0, 0) == None


def test_find_sticker_set_in_db_with_one_entry(mock_cursor):
    mock_cursor.execute(
        """
        INSERT INTO sticker_sets (
            dialog_id,
            message_id,
            pack_name,
            pack_link,
            sticker_set_id,
            access_hash
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (1, 10, "Pack", "Link", 123, 321),
    )
    assert find_sticker_set_in_db(mock_cursor, 123, 321) == (
        "Pack",
        "Link",
        123,
        321,
    )
