import pytest
import pytest_asyncio
import sqlite3
from objects.dialog import Dialog
from unittest.mock import MagicMock, AsyncMock, patch, call
from telethon import types


@pytest.fixture
def mock_client():
    client = AsyncMock()

    total_messages = MagicMock()
    total_messages.total = 10

    client.get_messages.return_value = total_messages

    return client


@pytest.fixture
def mock_dialog():
    dialog = MagicMock()

    entity = MagicMock()
    dialog.entity = entity
    dialog.id = 1

    dialog.name = "Me"

    return dialog


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.size_threshold = 5

    return config


@pytest.fixture
def mock_conn_and_cursor():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    return conn, cursor


@pytest.fixture
def checkpoint_fixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            dialog_id INTEGER,
            last_message_id INTEGER,
            message_counter INTEGER, 
            archiving_time FLOAT NOT NULL DEFAULT 0.0
        )
    """)

    cursor.execute("INSERT INTO dialogs (dialog_id) VALUES (?)", [1])

    yield cursor

    conn.close()


@pytest.fixture
def archive_message_fixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            message_id INTEGER ,
            author_name TEXT,
            views INTEGER,
            sender_id INTEGER,
            forward_from_username INTEGER,
            forward_from_user_id INTEGER,
            replied_to_id INTEGER,
            text TEXT,
            date DATETIME,
            edit_date DATETIME,
            file_path TEXT,
            file_id TEXT,
            file_size FLOAT NOT NULL DEFAULT 0.0,
            downloaded_file BOOL NOT NULL DEFAULT FALSE,
            UNIQUE (dialog_id, message_id)
        )
    """)

    yield cursor

    conn.close()


@pytest_asyncio.fixture
@patch("objects.dialog.Dialog.get_checkpoint")
@patch("objects.dialog.file")
@patch("objects.dialog.prog")
@patch("objects.dialog.err")
@patch("objects.dialog.make_tables")
@patch("objects.dialog.Dialog.get_dialog_type")
@patch("telethon.utils.get_peer_id")
@patch("sqlite3.connect")
@patch("logging.Logger.info")
async def mock_dialog_class(
    mock_logger,
    mock_connect,
    mock_get_id,
    mock_get_type,
    mock_make_tables,
    mock_error,
    mock_progress,
    mock_file,
    mock_checkpoint,
    mock_client,
    mock_dialog,
    mock_config,
    mock_conn_and_cursor,
):
    progress = MagicMock()
    file = MagicMock()
    error = MagicMock()

    mock_connect.return_value = mock_conn_and_cursor[0]

    mock_get_id.return_value = 1
    mock_get_type.return_value = "Something"

    mock_error.return_value = error
    mock_progress.return_value = progress
    mock_file.return_value = file

    mock_checkpoint.return_value = [123]

    obj = Dialog(mock_client, mock_config, mock_dialog)
    await obj.set_up()

    return {
        "obj": obj,
        "mock_dialog": mock_dialog,
        "mock_client": mock_client,
        "mock_config": mock_config,
        "mock_logger": mock_logger,
        "mock_connect": mock_connect,
        "mock_get_id": mock_get_id,
        "mock_get_type": mock_get_type,
        "mock_make_tables": mock_make_tables,
        "mock_conn_and_cursor": mock_conn_and_cursor,
        "mock_progress": mock_progress,
        "progress": progress,
        "mock_file": mock_file,
        "file": file,
        "mock_error": mock_error,
        "mock_checkpoint": mock_checkpoint,
        "progress": progress,
    }


@pytest.mark.asyncio
async def test_dialog_init(mock_dialog_class):
    assert mock_dialog_class["obj"].client is mock_dialog_class["mock_client"]
    assert mock_dialog_class["obj"].dialog is mock_dialog_class["mock_dialog"]
    assert mock_dialog_class["obj"].entity is mock_dialog_class["mock_dialog"].entity
    assert mock_dialog_class["obj"].config is mock_dialog_class["mock_config"]
    assert mock_dialog_class["obj"].id == 1
    assert mock_dialog_class["obj"].type == "Something"
    assert mock_dialog_class["obj"].total_messages == 10
    assert mock_dialog_class["mock_logger"].call_count == 2
    assert mock_dialog_class["mock_logger"].call_args_list == [
        call("Initiating the dialog class (the synchronous part)..."),
        call("Initiating the dialog class (the asynchronous part)..."),
    ]
    mock_dialog_class["mock_connect"].assert_called_once_with("telegram.db")
    mock_dialog_class["mock_get_id"].assert_called_once_with(
        mock_dialog_class["mock_dialog"].entity
    )
    mock_dialog_class["mock_get_type"].assert_called_once()
    mock_dialog_class["mock_make_tables"].assert_called_once_with(
        mock_dialog_class["mock_conn_and_cursor"][1]
    )

    assert mock_dialog_class["mock_conn_and_cursor"][1].execute.call_count == 2
    assert mock_dialog_class["mock_conn_and_cursor"][1].execute.call_args_list == [
        call(
            "INSERT OR IGNORE INTO dialogs (dialog_id, name, type) VALUES  (?, ?, ?)",
            [1, "Me", "Something"],
        ),
        call(
            "UPDATE dialogs SET total_number_of_messages = ? WHERE dialog_id = ?",
            [10, 1],
        ),
    ]

    assert mock_dialog_class["mock_conn_and_cursor"][0].commit.call_count == 2

    mock_dialog_class["mock_client"].get_messages.assert_awaited_once_with(
        mock_dialog_class["mock_dialog"], limit=0
    )
    mock_dialog_class["mock_progress"].assert_called_once_with(10, "Me")
    mock_dialog_class["mock_file"].assert_called_once_with(5)
    mock_dialog_class["mock_error"].assert_called_once_with(
        mock_dialog_class["mock_conn_and_cursor"][0],
        mock_dialog_class["progress"],
        mock_dialog_class["obj"],
    )
    mock_dialog_class["mock_checkpoint"].assert_called_once()
    mock_dialog_class["progress"].use_checkpoint.assert_called_once_with([123])
    mock_dialog_class["obj"].users = set()


def test_dialog_get_type_with_user(mock_dialog_class):
    obj = mock_dialog_class["obj"]
    entity = MagicMock(spec=types.User)
    obj.entity = entity
    assert obj.get_dialog_type() == "User"


def test_dialog_get_type_with_chat(mock_dialog_class):
    obj = mock_dialog_class["obj"]
    entity = MagicMock(spec=types.Chat)
    obj.entity = entity
    assert obj.get_dialog_type() == "Chat"


def test_dialog_get_type_with_channel(mock_dialog_class):
    obj = mock_dialog_class["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = True
    obj.entity = entity
    assert obj.get_dialog_type() == "Channel"


def test_dialog_get_type_with_supergroup(mock_dialog_class):
    # .megagroup
    obj = mock_dialog_class["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = False
    obj.entity = entity
    assert obj.get_dialog_type() == "Supergroup"


def test_dialog_get_type_with_unknown(mock_dialog_class):
    obj = mock_dialog_class["obj"]
    entity = MagicMock()
    obj.entity = entity
    assert obj.get_dialog_type() == "Unknown"


@patch("objects.dialog.Dialog.get_checkpoint")
@patch("time.perf_counter")
def test_dialog_save_checkpoint(
    mock_counter, mock_get_checkpoint, mock_dialog_class, checkpoint_fixture
):
    obj = mock_dialog_class["obj"]
    progress = mock_dialog_class["progress"]

    progress.last_message_id = 33
    progress.message_counter = 3

    mock_counter.return_value = 3.3
    progress.time_start = 3.1

    obj.cursor = checkpoint_fixture

    mock_get_checkpoint.return_value = (None, None, 0.0)

    obj.save_checkpoint()

    checkpoint_fixture.execute("SELECT * FROM dialogs")

    # Python floating point precision makes it so it's not 0.2
    assert (1, 33, 3, 0.19999999999999973) == checkpoint_fixture.fetchone()
    mock_get_checkpoint.assert_called_once()
    mock_counter.assert_called_once()


def test_dialog_get_checkpoint_with_empty_entry(mock_dialog_class, checkpoint_fixture):
    obj = mock_dialog_class["obj"]
    obj.cursor = checkpoint_fixture

    assert obj.get_checkpoint() == (None, None, 0.0)


def test_dialog_get_checkpoint_with_one_entry(mock_dialog_class, checkpoint_fixture):
    obj = mock_dialog_class["obj"]
    obj.cursor = checkpoint_fixture

    checkpoint_fixture.execute("""
        UPDATE dialogs SET
            last_message_id = 33,
            message_counter = 3,
            archiving_time = 3.3
        WHERE dialog_id = 1    
    """)

    assert obj.get_checkpoint() == (33, 3, 3.3)


def test_dialog_get_checkpoint_with_many_entries(mock_dialog_class, checkpoint_fixture):
    obj = mock_dialog_class["obj"]
    obj.cursor = checkpoint_fixture

    checkpoint_fixture.execute("""
        UPDATE dialogs SET
            last_message_id = 33,
            message_counter = 3,
            archiving_time = 3.3
        WHERE dialog_id = 1    
    """)

    checkpoint_fixture.execute("INSERT INTO dialogs (dialog_id) VALUES (2)")

    assert obj.get_checkpoint() == (33, 3, 3.3)


@patch("objects.dialog.Dialog.save_checkpoint")
@patch("objects.dialog.insert_users_ids")
def test_dialog_key_interruption_with_no_user_info(
    mock_insert, mock_save, mock_dialog_class, capsys
):
    obj = mock_dialog_class["obj"]

    conn = mock_dialog_class["mock_conn_and_cursor"][0]

    config = mock_dialog_class["mock_config"]
    config.user_info = False

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mock_save.assert_called_once()
    mock_insert.assert_not_called()

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@patch("objects.dialog.Dialog.save_checkpoint")
@patch("objects.dialog.insert_users_ids")
def test_dialog_key_interruption_with_one_user(mock_insert, mock_save, mock_dialog_class, capsys):
    obj = mock_dialog_class["obj"]
    obj.users = {1}

    conn = mock_dialog_class["mock_conn_and_cursor"][0]

    config = mock_dialog_class["mock_config"]
    config.user_info = True

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mock_save.assert_called_once()
    mock_insert.assert_called_once_with(mock_dialog_class["mock_conn_and_cursor"][1], 1, 1)

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@patch("objects.dialog.Dialog.save_checkpoint")
@patch("objects.dialog.insert_users_ids")
def test_dialog_key_interruption_with_many_users(mock_insert, mock_save, mock_dialog_class, capsys):
    obj = mock_dialog_class["obj"]
    obj.users = {1, 2}

    conn = mock_dialog_class["mock_conn_and_cursor"][0]

    config = mock_dialog_class["mock_config"]
    config.user_info = True

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mock_save.assert_called_once()

    assert mock_insert.call_count == 2
    assert mock_insert.call_args_list == [
        call(mock_dialog_class["mock_conn_and_cursor"][1], 1, 1),
        call(mock_dialog_class["mock_conn_and_cursor"][1], 2, 1),
    ]

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@pytest.mark.asyncio
@patch("objects.dialog.user_id_handler")
@patch("objects.dialog.forward_handler")
@patch("objects.dialog.reply_handler")
@patch("objects.dialog.text_handler")
@patch("objects.dialog.reaction_handler", new_callable=AsyncMock)
async def test_dialog_archive_message(
    mock_reaction,
    mock_text,
    mock_reply,
    mock_forward,
    mock_user,
    mock_dialog_class,
    archive_message_fixture,
):
    obj = mock_dialog_class["obj"]
    config = mock_dialog_class["mock_config"]
    file = mock_dialog_class["file"]
    progress = mock_dialog_class["progress"]

    message = MagicMock()
    message.id = 33
    message.views = 600
    message.file = MagicMock()
    message.file.size = 100
    message.date = "Today"
    message.edit_date = "Just now"

    config.texts = True
    config.files = True
    config.reactions = True

    file.handle = AsyncMock()
    file.handle.return_value = ["There", "Secret", 3.0, 1]

    progress.used_space_in_MB = 25

    obj.cursor = archive_message_fixture

    mock_user.return_value = ["Me", 5]
    mock_forward.return_value = ["He", 17]
    mock_reply.return_value = 32
    mock_text.return_value = "Noice day"

    await obj.archive_message(message)

    mock_user.assert_called_once_with(message, obj.users)
    mock_forward.assert_called_once_with(message, obj.users)
    mock_reply.assert_called_once_with(message, obj.users)
    mock_text.assert_called_once_with(message)

    file.handle.assert_awaited_once_with(message)
    assert progress.used_space_in_MB == 25

    mock_reaction.assert_awaited_once_with(
        mock_dialog_class["mock_client"],
        mock_dialog_class["mock_dialog"],
        message,
        archive_message_fixture,
    )

    archive_message_fixture.execute("SELECT * FROM messages")

    assert (
        1,
        1,
        33,
        "Me",
        600,
        5,
        "He",
        17,
        32,
        "Noice day",
        "Today",
        "Just now",
        "There",
        "Secret",
        3.0,
        1,
    ) == archive_message_fixture.fetchone()
