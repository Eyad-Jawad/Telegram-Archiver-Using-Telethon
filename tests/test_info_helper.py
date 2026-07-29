import pytest
import sqlite3
from helpers.info import *
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from telethon import types
from telethon.errors import BadRequestError, ChannelPrivateError, ChatAdminRequiredError


@pytest.fixture
def cursor():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    yield cursor

    conn.close()


@pytest.fixture
def latest_photo_fixture(cursor):
    cursor.execute("""
        CREATE TABLE dialog_photos (
            dialog_id INTEGER,
            photo_date DATETIME
        )
    """)

    return cursor


@pytest.fixture
def is_archived_fixture(cursor):
    cursor.execute("""
        CREATE TABLE dialog_metadata (
            dialog_id INTEGER UNIQUE,
            full_request TEXT,
            date_of_request DATETIME
        )
    """)

    return cursor


@pytest.fixture
def push_info_fixture(is_archived_fixture):
    cursor = is_archived_fixture

    cursor.execute("""
        CREATE TABLE dialog_metadata_archive (
            dialog_id INTEGER,
            full_request TEXT,
            date_of_request DATETIME,
            UNIQUE (dialog_id, full_request)
        )
    """)

    return cursor


@pytest.fixture
def push_photos_fixture(cursor):
    cursor.execute("""
        CREATE TABLE dialog_photos (
            dialog_id INTEGER,
            photo_id INTEGER,
            photo_path TEXT,
            photo_date DATETIME
        )
    """)

    return cursor


@pytest.fixture
def insert_users_fixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            user_id INTEGER,
            dialog_id INTEGER,
            UNIQUE(user_id, dialog_id)
        )
    """)

    yield cursor

    conn.close()


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
        datetime(1900, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 10, 10, 10, 10, tzinfo=timezone.utc),
        datetime(2026, 5, 10, 10, 10, 10, tzinfo=timezone.utc),
        datetime(2026, 10, 10, 10, 10, 10, tzinfo=timezone.utc),
    ]


def test_get_latest_photo_date_for_empty_DB(latest_photo_fixture):
    assert get_latest_photo_date(latest_photo_fixture, 21) == date_consts()[0]


def test_get_latest_photo_date_for_empty_entry(latest_photo_fixture):
    cursor = latest_photo_fixture

    cursor.execute("INSERT INTO dialog_photos (dialog_id) VALUES (?)", [1])
    assert get_latest_photo_date(cursor, 1) == date_consts()[0]


def test_get_latest_photo_date_for_one_entry(latest_photo_fixture):
    cursor = latest_photo_fixture

    DATES = date_consts()

    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [1, datetime.isoformat(DATES[1])],
    )
    assert get_latest_photo_date(cursor, 1) == DATES[1]


def test_get_latest_photo_date_for_many_dates(latest_photo_fixture):
    cursor = latest_photo_fixture

    DATES = date_consts()

    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [1, datetime.isoformat(DATES[1])],
    )
    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [1, datetime.isoformat(DATES[2])],
    )
    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [1, datetime.isoformat(DATES[3])],
    )

    assert get_latest_photo_date(cursor, 1) == DATES[3]


def test_get_latest_photo_date_for_many_entries(latest_photo_fixture):
    cursor = latest_photo_fixture

    DATES = date_consts()

    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [1, datetime.isoformat(DATES[1])],
    )
    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [2, datetime.isoformat(DATES[2])],
    )
    cursor.execute(
        "INSERT INTO dialog_photos (dialog_id, photo_date) VALUES (?, ?)",
        [3, datetime.isoformat(DATES[3])],
    )

    assert get_latest_photo_date(cursor, 1) == DATES[1]


def test_is_archived_for_empty_DB(is_archived_fixture):
    assert is_archived(is_archived_fixture, 123) == False


@pytest.mark.parametrize(
    ("full_request, output"),
    [(None, False), ("Chickens", True)],
)
def test_is_archived_for_one_entry(is_archived_fixture, full_request, output):
    cursor = is_archived_fixture

    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request) VALUES (?, ?)",
        [1, full_request],
    )
    assert is_archived(cursor, 1) == output


def test_is_archived_for_many_entries(is_archived_fixture):
    cursor = is_archived_fixture

    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request) VALUES (?, ?)", [1, None]
    )
    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request) VALUES (?, ?)", [2, None]
    )
    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request) VALUES (?, ?)",
        [3, "Chickens"],
    )
    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request) VALUES (?, ?)",
        [4, "Chicken Wings"],
    )
    assert is_archived(cursor, 1) == False
    assert is_archived(cursor, 3) == True


def test_push_info_for_not_archived(push_info_fixture):
    cursor = push_info_fixture

    cursor.execute("INSERT INTO dialog_metadata (dialog_id) VALUES (?)", [1])
    insert_info_into_appropriate_table(cursor, 1, "Chickens")

    cursor.execute("SELECT full_request FROM dialog_metadata WHERE dialog_id = 1")

    assert "Chickens" == cursor.fetchone()[0]


@patch("helpers.info.datetime")
def test_push_info_with_archived(mock_datetime, push_info_fixture):
    cursor = push_info_fixture

    mock_datetime.now.return_value = "Just now"

    cursor.execute(
        "INSERT INTO dialog_metadata (dialog_id, full_request, date_of_request) VALUES (?, ?, ?)",
        [1, "Chickens", "Today"],
    )
    insert_info_into_appropriate_table(cursor, 1, "Chicken wings")

    cursor.execute("SELECT * FROM dialog_metadata WHERE dialog_id = 1")

    assert (1, "Chicken wings", "Just now") == cursor.fetchone()

    cursor.execute("SELECT * FROM dialog_metadata_archive WHERE dialog_id = 1")

    assert (1, "Chickens", "Today") == cursor.fetchone()


@pytest.mark.parametrize(
    ("photo_data"),
    [None, [], [[]]],
)
def test_push_photos_info_with_nothing(push_photos_fixture, photo_data):
    cursor = push_photos_fixture
    insert_photo_info(cursor, photo_data)

    cursor.execute("SELECT * FROM dialog_photos")

    assert None == cursor.fetchone()


def test_push_photos_info_with_one_entry(push_photos_fixture):
    cursor = push_photos_fixture

    photo_info = [(1, 1231, "Somewhere", "Sqlite parses time as str anyway")]

    insert_photo_info(cursor, photo_info)

    cursor.execute("SELECT * FROM dialog_photos")

    assert photo_info == (cursor.fetchall())


def test_push_photos_info_with_many_entries(push_photos_fixture):
    cursor = push_photos_fixture

    photo_info = [
        (1, 1234, "somewhere", "idk"),
        (1, 2314, "somewhere", "idk"),
        (1, 4321, "somewhere", "idk"),
    ]

    insert_photo_info(cursor, photo_info)

    cursor.execute("SELECT * FROM dialog_photos")

    assert photo_info == (cursor.fetchall())


@pytest.mark.parametrize("dialog_id, output", [(1, (1, None, None)), (None, None)])
def test_ensure_dialog_row_exists_with_no_row(is_archived_fixture, dialog_id, output):
    cursor = is_archived_fixture

    ensure_dialog_row_exists(cursor, dialog_id)

    cursor.execute("SELECT * FROM dialog_metadata")

    assert output == cursor.fetchone()


def test_ensure_dialog_row_exists_with_one_row(is_archived_fixture):
    cursor = is_archived_fixture

    cursor.execute("INSERT INTO dialog_metadata (dialog_id) VALUES (1)")

    ensure_dialog_row_exists(cursor, 1)

    cursor.execute("SELECT * FROM dialog_metadata")

    assert (1, None, None) == cursor.fetchone()


@pytest.mark.asyncio
@patch("helpers.info.ensure_dialog_row_exists")
@patch("helpers.info.get_full_request", new_callable=AsyncMock)
@patch("helpers.info.insert_info_into_appropriate_table")
@patch("helpers.info.get_latest_photo_date")
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
    mock_ensure,
):
    client = MagicMock()
    dialog = MagicMock()
    dialog.entity = MagicMock()
    dialog.entity.id = 1
    users = set()
    errors_handler = AsyncMock()
    cursor = MagicMock()

    errors_handler.handle = AsyncMock()

    full_request = mock_full_request.return_value
    latest_photo_date = mock_get_latest.return_value
    photo_info = mock_get_photo.return_value

    await get_dialog_info(client, dialog, users, errors_handler, cursor)

    mock_add_users.assert_awaited_once_with(
        client, dialog.entity, users, errors_handler
    )
    mock_push_photo.assert_called_once_with(cursor, photo_info)
    mock_get_photo.assert_awaited_once_with(
        client, dialog.entity, errors_handler, latest_photo_date
    )
    mock_get_latest.assert_called_once_with(cursor, 1)
    mock_push_into.assert_called_once_with(cursor, 1, full_request)
    mock_full_request.assert_awaited_once_with(client, dialog.entity, errors_handler)
    mock_ensure.assert_called_once_with(cursor, 1)
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
    photo.date = DATES[2]

    iterator = MagicMock()
    iterator.__aiter__.return_value = [photo]

    client.iter_profile_photos = MagicMock(return_value=iterator)

    client.download_media = AsyncMock()
    client.download_media.return_value = "Noice"

    errors_handler.handle = AsyncMock()

    assert await get_photo_info(client, dialog, errors_handler, DATES[1]) == [
        (1, 5, "Noice", "2026-05-10T10:10:10+00:00")
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


def test_insert_users_with_no_entry(insert_users_fixture):
    cursor = insert_users_fixture

    insert_users_ids(cursor, None, 1)
    insert_users_ids(cursor, 1, None)
    insert_users_ids(cursor, None, None)

    cursor.execute("SELECT * FROM users")

    assert None == cursor.fetchone()


def test_insert_users_with_one_entry(insert_users_fixture):
    cursor = insert_users_fixture

    insert_users_ids(cursor, 1, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12)] == cursor.fetchall()


def test_insert_users_with_many_entreis(insert_users_fixture):
    cursor = insert_users_fixture

    insert_users_ids(cursor, 1, 12)
    insert_users_ids(cursor, 1, 11)
    insert_users_ids(cursor, 2, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12), (1, 11), (2, 12)] == cursor.fetchall()


def test_insert_users_duplicate(insert_users_fixture):
    cursor = insert_users_fixture

    insert_users_ids(cursor, 1, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12)] == cursor.fetchall()

    insert_users_ids(cursor, 1, 12)

    assert [[]] == [cursor.fetchall()]  # It's empty because it the db just fetched


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
    cursor = MagicMock()
    users = {5}

    dialog.entity.id = 1
    await entity_handler(client, dialog, users, errors_handler, cursor, True)

    mock_insert.assert_called_once_with(cursor, 5, 1)
    mock_info.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.info.SimpleNamespace")
@patch("helpers.info.insert_users_ids")
@patch("helpers.info.get_dialog_info", new_callable=AsyncMock)
async def test_entity_handler_with_one_entry_and_no_skip(mock_info, mock_insert, mock_namespace):
    client = AsyncMock()
    entity = MagicMock()
    fake_dialog = MagicMock()
    dialog = MagicMock()
    errors_handler = MagicMock()
    cursor = MagicMock()
    users = {5}

    dialog.entity.id = 1
    client.get_entity.return_value = entity
    mock_namespace.return_value = fake_dialog
    await entity_handler(client, dialog, users, errors_handler, cursor, False)

    mock_insert.assert_called_once_with(cursor, 5, 1)
    client.get_entity.assert_awaited_once_with(5)
    mock_namespace.assert_called_once_with(entity=entity)
    mock_info.assert_awaited_once_with(client, fake_dialog, set(), errors_handler, cursor)
