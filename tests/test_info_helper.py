from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from telethon import types

from db.models import DialogMetadata, DialogPhoto, User
from helpers.info import *


@pytest.mark.parametrize(
    "post_author_input",
    ["eyad", "EYAD", "\\//\\//", "12", "🥀something"],
)
def test_user_id_handler_with_post_author(post_author_input):
    message = MagicMock()
    message.post_author = post_author_input
    users_set = set()

    assert user_id_handler(message, users_set) == (post_author_input, 0)
    assert len(users_set) == 0


def test_user_id_handler_with_sender_id():
    message = MagicMock()
    message.post_author = None
    message.sender_id = 1234

    assert user_id_handler(message, set()) == ("", 1234)


def test_user_id_handler_with_no_sender_id():
    message = MagicMock()
    message.post_author = None
    message.sender_id = None

    assert user_id_handler(message, set()) == ("", 0)


def test_user_id_handler_for_users_set():
    users_set = set()

    message = MagicMock()
    message.post_author = None
    message.sender_id = 1234

    user_id_handler(message, users_set)

    assert users_set == {1234}

    message.sender_id = 4321

    user_id_handler(message, users_set)

    assert users_set == {1234, 4321}

    user_id_handler(message, users_set)

    assert users_set == {1234, 4321}


def date_consts():
    return [
        datetime(1900, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 10, 10, 10, 10, tzinfo=UTC),
        datetime(2026, 5, 10, 10, 10, 10, tzinfo=UTC),
        datetime(2026, 10, 10, 10, 10, 10, tzinfo=UTC),
    ]


@pytest.mark.asyncio
async def test_get_latest_photo_date_for_empty_DB(mock_session):
    assert await get_latest_photo_date(mock_session, 21) == date_consts()[0]


@pytest.mark.asyncio
async def test_get_latest_photo_date_for_empty_entry(mock_session):
    new_dialog_photo = DialogPhoto(
        dialog_id=1,
        photo_id="Anything",
        photo_path="Anything",
        photo_date=date_consts()[0],
    )
    mock_session.add(new_dialog_photo)

    assert await get_latest_photo_date(mock_session, 1) == date_consts()[0]


@pytest.mark.asyncio
async def test_get_latest_photo_date_for_one_entry(mock_session):
    DATES = date_consts()

    mock_session.add(
        DialogPhoto(
            dialog_id=1,
            photo_date=DATES[1],
            photo_id="Anything",
            photo_path="Anything",
        )
    )
    assert await get_latest_photo_date(mock_session, 1) == DATES[1]


@pytest.mark.asyncio
async def test_get_latest_photo_date_for_many_dates(mock_session):
    DATES = date_consts()
    mock_session.add(
        DialogPhoto(
            dialog_id=1,
            photo_date=DATES[1],
            photo_id="Anything",
            photo_path="Anything",
        )
    )
    mock_session.add(
        DialogPhoto(
            dialog_id=1,
            photo_date=DATES[2],
            photo_id="Anything",
            photo_path="Anything",
        )
    )
    mock_session.add(
        DialogPhoto(
            dialog_id=1,
            photo_date=DATES[3],
            photo_id="Anything",
            photo_path="Anything",
        )
    )

    assert await get_latest_photo_date(mock_session, 1) == DATES[3]


@pytest.mark.asyncio
async def test_get_latest_photo_date_for_many_entries(mock_session):
    DATES = date_consts()

    mock_session.add(
        DialogPhoto(
            dialog_id=1,
            photo_date=DATES[1],
            photo_id="Anything",
            photo_path="Anything",
        )
    )
    mock_session.add(
        DialogPhoto(
            dialog_id=2,
            photo_date=DATES[2],
            photo_id="Anything",
            photo_path="Anything",
        )
    )
    mock_session.add(
        DialogPhoto(
            dialog_id=3,
            photo_date=DATES[3],
            photo_id="Anything",
            photo_path="Anything",
        )
    )

    assert await get_latest_photo_date(mock_session, 1) == DATES[1]


@pytest.mark.asyncio
async def test_push_info_with_one_entry(mock_session):
    mock_session.add(DialogMetadata(dialog_id=1, full_request="Anything"))
    insert_dialog_metadata(mock_session, 1, "Chickens")

    stmt = select(DialogMetadata.full_request).where(
        DialogMetadata.dialog_id == 1
    )
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [("Anything",), ("Chickens",)] == result


@pytest.mark.asyncio
@patch("db.models.dialogs_metadata.datetime")
async def test_push_info_with_many_entries(mock_time, mock_session):
    DATES = date_consts()
    mock_time.now.return_value = DATES[2]

    mock_session.add(
        DialogMetadata(
            dialog_id=1, full_request="Chickens", date_of_request=DATES[1]
        )
    )

    insert_dialog_metadata(mock_session, 1, "Chicken wings")

    stmt = select(
        DialogMetadata.dialog_id,
        DialogMetadata.full_request,
        DialogMetadata.date_of_request,
    ).where(DialogMetadata.dialog_id == 1)

    result = await mock_session.execute(stmt)
    result = result.all()

    assert [(1, "Chickens", DATES[1]), (1, "Chicken wings", DATES[2])] == result

    mock_time.now.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("photo_data"),
    [None, [], [[]]],
)
async def test_push_photos_info_with_nothing(mock_session, photo_data):
    insert_photo_info(mock_session, photo_data)

    stmt = select(
        DialogPhoto.dialog_id,
        DialogPhoto.photo_id,
        DialogPhoto.photo_path,
        DialogPhoto.photo_date,
    )
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [] == result


@pytest.mark.asyncio
async def test_push_photos_info_with_one_entry(mock_session):
    DATES = date_consts()
    photo_info = [(1, 1231, "Somewhere", DATES[1])]

    insert_photo_info(mock_session, photo_info)

    stmt = select(
        DialogPhoto.dialog_id,
        DialogPhoto.photo_id,
        DialogPhoto.photo_path,
        DialogPhoto.photo_date,
    )
    result = await mock_session.execute(stmt)
    result = result.all()

    assert photo_info == result


@pytest.mark.asyncio
async def test_push_photos_info_with_many_entries(mock_session):
    DATES = date_consts()
    photo_info = [
        (1, 1234, "somewhere", DATES[1]),
        (1, 2314, "somewhere", DATES[1]),
        (1, 4321, "somewhere", DATES[1]),
    ]

    insert_photo_info(mock_session, photo_info)

    stmt = select(
        DialogPhoto.dialog_id,
        DialogPhoto.photo_id,
        DialogPhoto.photo_path,
        DialogPhoto.photo_date,
    )
    result = await mock_session.execute(stmt)
    result = result.all()

    assert photo_info == result


@pytest.mark.asyncio
@patch("helpers.info.get_full_request", new_callable=AsyncMock)
@patch("helpers.info.insert_dialog_metadata")
@patch("helpers.info.get_latest_photo_date", new_callable=AsyncMock)
@patch("helpers.info.get_photo_info", new_callable=AsyncMock)
@patch("helpers.info.insert_photo_info")
@patch("helpers.info.add_users_to_set", new_callable=AsyncMock)
async def test_get_dialog_info(
    mock_add_users,
    mock_push_photo,
    mock_get_photo,
    mock_get_latest,
    mock_push_into,
    mock_full_request,
):
    client = MagicMock()
    dialog = MagicMock()
    dialog.entity = MagicMock()
    dialog.id = 1
    dialog.entity.id = 1
    users = set()
    errors_handler = AsyncMock()
    session = MagicMock()

    errors_handler.handle = AsyncMock()

    full_request = mock_full_request.return_value
    latest_photo_date = mock_get_latest.return_value
    photo_info = mock_get_photo.return_value

    await get_dialog_info(client, dialog, users, errors_handler, session)

    mock_add_users.assert_awaited_once_with(
        client, dialog, users, errors_handler
    )
    mock_push_photo.assert_called_once_with(session, photo_info)
    mock_get_photo.assert_awaited_once_with(
        client, dialog.entity, errors_handler, latest_photo_date
    )
    mock_get_latest.assert_awaited_once_with(session, 1)
    mock_push_into.assert_called_once_with(session, 1, full_request)
    mock_full_request.assert_awaited_once_with(
        client, dialog.entity, errors_handler
    )
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@patch("telethon.functions.channels.GetFullChannelRequest")
async def test_get_full_request_for_channel(mock_channel):
    client = AsyncMock()
    dialog = MagicMock(spec=types.Channel)
    dialog.id = 1
    errors_handler = AsyncMock()
    result = MagicMock()

    errors_handler.handle = AsyncMock()

    mock_channel.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result

    assert await get_full_request(client, dialog, errors_handler) == "Chickens"
    mock_channel.assert_called_once_with(1)
    client.assert_awaited_once_with("Test")
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@patch("telethon.functions.users.GetFullUserRequest")
async def test_get_full_request_for_user(mock_user):
    client = AsyncMock()
    dialog = MagicMock(spec=types.User)
    dialog.id = 1
    errors_handler = AsyncMock()
    result = MagicMock()

    errors_handler.handle = AsyncMock()

    mock_user.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result

    assert await get_full_request(client, dialog, errors_handler) == "Chickens"
    mock_user.assert_called_once_with(1)
    client.assert_awaited_once_with("Test")
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetFullChatRequest")
async def test_get_full_request_for_chat(mock_chat):
    client = AsyncMock()
    dialog = MagicMock(spec=types.Chat)
    dialog.id = 1
    errors_handler = AsyncMock()
    result = MagicMock()

    errors_handler.handle = AsyncMock()

    mock_chat.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result

    assert await get_full_request(client, dialog, errors_handler) == "Chickens"
    mock_chat.assert_called_once_with(1)
    client.assert_awaited_once_with("Test")
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@patch("logging.Logger.warning")
async def test_get_full_request_for_unknown_type(mock_logger):
    dialog = MagicMock()
    errors_handler = AsyncMock()
    errors_handler.handle = AsyncMock()

    assert await get_full_request(None, dialog, errors_handler) == ""
    mock_logger.assert_called_once_with(f"Unknown dialog type: {dialog}")
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetFullChatRequest")
async def test_get_full_request_for_error(chat_mock):
    client = AsyncMock(side_effect=RuntimeError("Idk what"))
    dialog = MagicMock(spec=types.Chat)
    dialog.id = 1
    dialog.name = "Idk what"
    errors_handler = MagicMock()
    errors_handler.handle = AsyncMock()

    await get_full_request(client, dialog, errors_handler)

    client.assert_awaited_once()
    chat_mock.assert_called_once_with(1)
    errors_handler.handle.assert_awaited_once_with(client.side_effect)


@pytest.mark.asyncio
async def test_get_photo_info_for_empty_input():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()

    errors_handler.handle = AsyncMock()

    iterator = MagicMock()
    iterator.__aiter__.return_value = []

    client.iter_profile_photos = MagicMock(return_value=iterator)

    assert await get_photo_info(client, dialog, errors_handler, None) == []
    client.iter_profile_photos.assert_called_once_with(dialog)
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_photo_info_for_one_input():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    photo = MagicMock()

    DATES = date_consts()

    dialog.id = 1

    photo.id = 5
    photo.date = DATES[1]

    iterator = MagicMock()
    iterator.__aiter__.return_value = [photo]

    client.iter_profile_photos = MagicMock(return_value=iterator)

    client.download_media = AsyncMock()
    client.download_media.return_value = "Noice"

    errors_handler.handle = AsyncMock()

    assert await get_photo_info(client, dialog, errors_handler, DATES[1]) == [
        (1, 5, "Noice", DATES[1])
    ]
    client.iter_profile_photos.assert_called_once_with(dialog)
    client.download_media.assert_awaited_once_with(photo, file="Media/")
    errors_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_photo_info_for_error():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()

    error = RuntimeError("dunno")

    client.iter_profile_photos = MagicMock(side_effect=error)

    errors_handler.handle = AsyncMock()

    assert await get_photo_info(client, dialog, errors_handler, None) == []
    client.iter_profile_photos.assert_called_once_with(dialog)
    errors_handler.handle.assert_awaited_once_with(error)


@pytest.mark.asyncio
async def test_add_users_to_set_with_empty_input():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    users = set()

    errors_handler.handle = AsyncMock()

    iterator = MagicMock()
    iterator.__aiter__.return_value = []

    client.iter_participants.return_value = iterator

    await add_users_to_set(client, dialog, users, errors_handler)

    client.iter_participants.assert_called_once_with(dialog)
    errors_handler.handle.assert_not_awaited()
    assert users == set()


@pytest.mark.asyncio
async def test_add_users_to_set_with_one_input():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    users = set()

    errors_handler.handle = AsyncMock()

    user = MagicMock()
    user.id = 1

    iterator = MagicMock()
    iterator.__aiter__.return_value = [user]

    client.iter_participants.return_value = iterator

    await add_users_to_set(client, dialog, users, errors_handler)

    client.iter_participants.assert_called_once_with(dialog)
    errors_handler.handle.assert_not_awaited()
    assert users == {1}


@pytest.mark.asyncio
async def test_add_users_to_set_with_many_inputs():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    users = {1, 5}

    errors_handler.handle = AsyncMock()

    user1 = MagicMock()
    user1.id = 1

    user2 = MagicMock()
    user2.id = 2

    user3 = MagicMock()
    user3.id = 3

    user4 = MagicMock()
    user4.id = 4

    iterator = MagicMock()
    iterator.__aiter__.return_value = [user1, user2, user3, user4]

    client.iter_participants.return_value = iterator

    await add_users_to_set(client, dialog, users, errors_handler)

    client.iter_participants.assert_called_once_with(dialog)
    errors_handler.handle.assert_not_awaited()
    assert users == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
async def test_add_users_to_set_for_unknown_errors():
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()

    errors_handler.handle = AsyncMock()

    error = RuntimeError("Dunno")

    client.iter_participants = MagicMock(side_effect=error)

    await add_users_to_set(client, dialog, None, errors_handler)

    client.iter_participants.assert_called_once_with(dialog)
    errors_handler.handle.assert_awaited_once_with(error)


@pytest.mark.asyncio
async def test_insert_users_with_no_entry(mock_session):
    insert_users_ids(mock_session, None, 1)
    insert_users_ids(mock_session, 1, None)
    insert_users_ids(mock_session, None, None)

    stmt = select(User.user_id, User.dialog_id)
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [] == result


@pytest.mark.asyncio
async def test_insert_users_with_one_entry(mock_session):
    insert_users_ids(mock_session, 1, 12)

    stmt = select(User.user_id, User.dialog_id)
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [(1, 12)] == result


@pytest.mark.asyncio
async def test_insert_users_with_many_entreis(mock_session):
    insert_users_ids(mock_session, 1, 12)
    insert_users_ids(mock_session, 1, 11)
    insert_users_ids(mock_session, 2, 12)

    stmt = select(User.user_id, User.dialog_id)
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [(1, 12), (1, 11), (2, 12)] == result


@pytest.mark.asyncio
async def test_insert_users_duplicate(mock_session):
    insert_users_ids(mock_session, 1, 12)

    stmt = select(User.user_id, User.dialog_id)
    result = await mock_session.execute(stmt)
    result = result.all()

    assert [(1, 12)] == result

    insert_users_ids(mock_session, 1, 12)

    result = await mock_session.execute(stmt)
    result = result.all()

    assert [(1, 12)] == result


@pytest.mark.asyncio
@patch("helpers.info.insert_users_ids")
@patch("helpers.info.get_dialog_info", new_callable=AsyncMock)
async def test_entity_handler_with_empty_set(mock_info, mock_insert):
    await entity_handler(None, None, set(), None, None, True)

    mock_info.assert_not_awaited()
    mock_insert.assert_not_called()


@pytest.mark.asyncio
@patch("helpers.info.insert_users_ids")
@patch("helpers.info.get_dialog_info", new_callable=AsyncMock)
async def test_entity_handler_with_one_entry_and_skip(mock_info, mock_insert):
    client = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    session = MagicMock()
    users = {5}

    dialog.entity.id = 1
    await entity_handler(client, dialog, users, errors_handler, session, True)

    mock_insert.assert_called_once_with(session, 5, 1)
    mock_info.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.info.construct_fake_dialog")
@patch("helpers.info.insert_users_ids")
@patch("helpers.info.get_dialog_info", new_callable=AsyncMock)
async def test_entity_handler_with_one_entry_and_no_skip(
    mock_info, mock_insert, mock_construct_fake_dialog
):
    client = AsyncMock()
    entity = MagicMock()
    fake_dialog = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    session = MagicMock()
    users = {5}

    dialog.entity.id = 1
    client.get_entity.return_value = entity
    mock_construct_fake_dialog.return_value = fake_dialog
    await entity_handler(client, dialog, users, errors_handler, session, False)

    mock_insert.assert_called_once_with(session, 5, 1)
    client.get_entity.assert_awaited_once_with(5)
    mock_construct_fake_dialog.assert_called_once_with(entity)
    mock_info.assert_awaited_once_with(
        client, fake_dialog, set(), errors_handler, session
    )
