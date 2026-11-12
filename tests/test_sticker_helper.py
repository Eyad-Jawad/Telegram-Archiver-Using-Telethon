from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
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

@pytest_asyncio.fixture
async def one_sticker_set(mock_session):
    sticker_set = StickerSetInfo(
        title="pack", link="add", id=123, access_hash=321
    )
    insert_sticker_set_info(mock_session, 1, 10, sticker_set)

    stmt = select(StickerSet)
    result = await mock_session.execute(stmt)
    result = result.scalar_one()

    assert result.id == 1
    assert result.dialog_id == 1
    assert result.message_id == 10
    assert result.pack_name == sticker_set.title
    assert result.pack_link == sticker_set.link
    assert result.sticker_set_id == sticker_set.id
    assert result.access_hash == sticker_set.access_hash

    return mock_session

@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db", new_callable=AsyncMock)
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_no_message_or_file_or_sticker_set_or_empty_sticker_set(
    mock_get_info, mock_insert, mock_find
):
    await stickers_handler(None, None, None, None)  # No message

    message = MagicMock()
    message.file = None
    await stickers_handler(None, message, None, None)  # No file

    message.file = MagicMock()
    message.file.sticker_set = None
    await stickers_handler(None, message, None, None)  # No sticker set

    message.file.sticker_set = MagicMock(spec=types.InputStickerSetEmpty)
    await stickers_handler(None, message, None, None)  # Empty sticker set

    mock_get_info.assert_not_awaited()
    mock_insert.assert_not_called()
    mock_find.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db", new_callable=AsyncMock)
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_existing_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_session
):
    client = MagicMock()
    dialog_id = 1

    sticker_set = MagicMock()
    sticker_set.id = 123
    sticker_set.access_hash = 321
    mock_find.return_value = sticker_set
    
    await stickers_handler(client, mock_message, dialog_id, mock_session)

    mock_find.assert_awaited_once_with(mock_session, 123, 321)
    mock_insert.assert_called_once_with(
        mock_session, 1, 10, mock_find.return_value
    )
    mock_get_info.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.stickers.find_sticker_set_in_db", new_callable=AsyncMock)
@patch("helpers.stickers.insert_sticker_set_info")
@patch("helpers.stickers.get_sticker_set_info", new_callable=AsyncMock)
async def test_stickers_handler_with_new_sticker_set(
    mock_get_info, mock_insert, mock_find, mock_message, mock_session
):
    client = MagicMock()
    dialog_id = 1
    mock_find.return_value = None

    sticker_set = MagicMock()
    sticker_set.id = 123
    sticker_set.access_hash = 321
    mock_get_info.return_value = sticker_set

    await stickers_handler(client, mock_message, dialog_id, mock_session)

    mock_find.assert_awaited_once_with(mock_session, 123, 321)
    mock_insert.assert_called_once_with(
        mock_session, 1, 10, sticker_set,
    )
    mock_get_info.assert_awaited_once_with(
        client, mock_message.file.sticker_set
    )


@pytest.mark.asyncio
async def test_insert_sticker_set_info_with_no_entry(mock_session):
    insert_sticker_set_info(mock_session, None, None, None)

    stmt = select(StickerSet)
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [] == result


@pytest.mark.asyncio
async def test_insert_sticker_set_info_with_one_entry(one_sticker_set):
    pass

@pytest.mark.asyncio
async def test_insert_sticker_set_info_with_many_entries(one_sticker_set):
    mock_session = one_sticker_set

    sticker_set = StickerSetInfo(
        title="names", link="nah", id=654, access_hash=456,
    )
    insert_sticker_set_info(mock_session, 1, 11, sticker_set)

    stmt = select(StickerSet)
    result = await mock_session.execute(stmt)
    result = result.scalars().all()

    assert result[1].id == 2
    assert result[1].dialog_id == 1
    assert result[1].message_id == 11
    assert result[1].pack_name == sticker_set.title
    assert result[1].pack_link == sticker_set.link
    assert result[1].sticker_set_id == sticker_set.id
    assert result[1].access_hash == sticker_set.access_hash


@pytest.mark.filterwarnings(
    "ignore:Identity map already had an identity for.*:sqlalchemy.exc.SAWarning"
)
@pytest.mark.asyncio
async def test_insert_sticker_set_info_with_dupes(one_sticker_set):
    mock_session = one_sticker_set

    sticker_set = StickerSetInfo(
        title="names", link="nah", id=654, access_hash=456,
    )
    insert_sticker_set_info(mock_session, 1, 10, sticker_set)

    stmt = select(StickerSet)
    result = await mock_session.execute(stmt)
    result = result.scalars().all()

    assert result[0].id == 1
    assert result[0].dialog_id == 1
    assert result[0].message_id == 10
    assert result[0].pack_name == "pack"
    assert result[0].pack_link == "add"
    assert result[0].sticker_set_id == 123
    assert result[0].access_hash == 321


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

    result = await get_sticker_set_info(client, sticker_set) 
    assert result.title == "Pack"
    assert result.link == "https://t.me/addstickers/add"
    assert result.id == 123
    assert result.access_hash == 321

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
    result = await get_sticker_set_info(client, sticker_set)

    assert result.title == ""
    assert result.link == "Pack is unavailable"
    assert result.id == 123
    assert result.access_hash == 321

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
    result = await get_sticker_set_info(client, sticker_set) 

    assert result.title == ""
    assert result.link == ""
    assert result.id ==123
    assert result.access_hash == 321

    client.assert_awaited_once_with("called")
    mock_requset.assert_called_once_with(stickerset=sticker_set, hash=0)


@pytest.mark.asyncio
async def test_find_sticker_set_in_db_with_empty_db(mock_session):
    assert await find_sticker_set_in_db(mock_session, 0, 0) == None


@pytest.mark.asyncio
async def test_find_sticker_set_in_db_with_one_entry(mock_session):
    new_sticker_set = StickerSet(
        dialog_id=1,
        message_id=10,
        pack_name="Pack",
        pack_link="Link",
        sticker_set_id=123,
        access_hash=321,
    )

    mock_session.add(new_sticker_set)
    await mock_session.commit()

    result = await find_sticker_set_in_db(mock_session, 123, 321)

    assert result.title == "Pack"
    assert result.link == "Link"
    assert result.id == 123
    assert result.access_hash == 321
