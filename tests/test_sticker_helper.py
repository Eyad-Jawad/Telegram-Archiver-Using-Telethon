from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from telethon import errors

from db.models import StickerSet
from helpers.stickers import *


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
async def test_stickers_handler_with_empty_sticker_set(
    mock_get_info, mock_insert, mock_find
):
    message = MagicMock()
    message.file = MagicMock()
    message.file.sticker_set = MagicMock(spec=types.InputStickerSetEmpty)
    await stickers_handler(None, message, None, None)

    mock_get_info.assert_not_awaited()
    mock_insert.assert_not_called()
    mock_find.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_existing_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_session
):
    client = MagicMock()
    dialog_id = 1
    mock_find.return_value = ("pack", "link", 123, 321)
    await stickers_handler(client, mock_message, dialog_id, mock_session)

    mock_find.assert_called_once_with(mock_session, 123, 321)
    mock_insert.assert_called_once_with(
        mock_session, (1, 10, "pack", "link", 123, 321)
    )
    mock_get_info.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db")
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_new_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_session
):
    client = MagicMock()
    dialog_id = 1
    mock_find.return_value = None
    mock_get_info.return_value = ("things", "add", 123, 321)
    await stickers_handler(client, mock_message, dialog_id, mock_session)

    mock_find.assert_called_once_with(mock_session, 123, 321)
    mock_insert.assert_called_once_with(
        mock_session, (1, 10, "things", "add", 123, 321)
    )
    mock_get_info.assert_awaited_once_with(
        client, mock_message.file.sticker_set
    )


def test_insert_sticker_set_info_with_no_entry(mock_session):
    insert_sticker_set_info(mock_session, None)

    result = mock_session.scalars(select(StickerSet)).all()

    assert [] == result


def test_insert_sticker_set_info_with_one_entry(mock_session):
    insert_sticker_set_info(mock_session, (1, 10, "pack", "add", 123, 321))

    result = (
        mock_session.query(
            StickerSet.id,
            StickerSet.dialog_id,
            StickerSet.message_id,
            StickerSet.pack_name,
            StickerSet.pack_link,
            StickerSet.sticker_set_id,
            StickerSet.access_hash,
        )
        .filter(StickerSet.dialog_id == 1)
        .all()
    )

    assert [(1, 1, 10, "pack", "add", 123, 321)] == result


def test_insert_sticker_set_info_with_many_entries(mock_session):
    insert_sticker_set_info(mock_session, (1, 10, "pack", "add", 123, 321))

    result = (
        mock_session.query(
            StickerSet.id,
            StickerSet.dialog_id,
            StickerSet.message_id,
            StickerSet.pack_name,
            StickerSet.pack_link,
            StickerSet.sticker_set_id,
            StickerSet.access_hash,
        )
        .filter(StickerSet.dialog_id == 1)
        .all()
    )

    assert [(1, 1, 10, "pack", "add", 123, 321)] == result

    insert_sticker_set_info(mock_session, (1, 10, "names", "nah", 654, 456))

    result = (
        mock_session.query(
            StickerSet.id,
            StickerSet.dialog_id,
            StickerSet.message_id,
            StickerSet.pack_name,
            StickerSet.pack_link,
            StickerSet.sticker_set_id,
            StickerSet.access_hash,
        )
        .filter(StickerSet.dialog_id == 1)
        .all()
    )

    assert [(1, 1, 10, "pack", "add", 123, 321)] == result


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetStickerSetRequest")
async def test_get_sticker_set_info_with_valid_sticker_set(
    mock_requset, mock_message
):
    client = AsyncMock()
    result = MagicMock()
    result.set.title = "Pack"
    result.set.short_name = "add"
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


def test_find_sticker_set_in_db_with_empty_db(mock_session):
    assert find_sticker_set_in_db(mock_session, 0, 0) == None


def test_find_sticker_set_in_db_with_one_entry(mock_session):
    new_sticker_set = StickerSet(
        dialog_id=1,
        message_id=10,
        pack_name="Pack",
        pack_link="Link",
        sticker_set_id=123,
        access_hash=321,
    )

    mock_session.add(new_sticker_set)

    assert find_sticker_set_in_db(mock_session, 123, 321) == (
        "Pack",
        "Link",
        123,
        321,
    )
