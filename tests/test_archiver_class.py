from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio
from telethon import types

from db.models import Dialog, Message
from objects.archiver import Archiver


def date_consts():
    return [
        datetime(1900, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 10, 10, 10, 10, tzinfo=UTC),
        datetime(2026, 5, 10, 10, 10, 10, tzinfo=UTC),
        datetime(2026, 10, 10, 10, 10, 10, tzinfo=UTC),
    ]


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


@pytest_asyncio.fixture
@patch("objects.archiver.Archiver.get_checkpoint")
@patch("objects.archiver.file")
@patch("objects.archiver.prog")
@patch("objects.archiver.err")
@patch("objects.archiver.Dialog")
@patch("objects.archiver.get_session")
@patch("objects.archiver.Archiver.get_dialog_type")
@patch("telethon.utils.get_peer_id")
@patch("logging.Logger.info")
async def mock_archiver(
    mock_logger,
    mock_get_id,
    mock_get_type,
    mock_get_session,
    mock_db_dialog,
    mock_error,
    mock_progress,
    mock_file,
    mock_checkpoint,
    mock_client,
    mock_dialog,
    mock_config,
):
    progress = MagicMock()
    file = MagicMock()
    error = MagicMock()
    mock_session = MagicMock()

    mock_get_id.return_value = 1
    mock_get_type.return_value = "Something"

    mock_error.return_value = error
    mock_progress.return_value = progress
    mock_file.return_value = file

    mock_get_session.return_value = mock_session

    mock_checkpoint.return_value = [123]

    obj = Archiver(mock_client, mock_config, mock_dialog)
    await obj.set_up()

    return {
        "obj": obj,
        "mock_dialog": mock_dialog,
        "mock_client": mock_client,
        "mock_config": mock_config,
        "mock_logger": mock_logger,
        "mock_get_id": mock_get_id,
        "mock_get_type": mock_get_type,
        "mock_get_session": mock_get_session,
        "mock_db_dialog": mock_db_dialog,
        "mock_session": mock_session,
        "mock_progress": mock_progress,
        "progress": progress,
        "mock_file": mock_file,
        "file": file,
        "mock_error": mock_error,
        "mock_checkpoint": mock_checkpoint,
    }


@pytest.mark.asyncio
async def test_dialog_init(mock_archiver):
    assert mock_archiver["obj"].client is mock_archiver["mock_client"]
    assert mock_archiver["obj"].dialog is mock_archiver["mock_dialog"]
    assert mock_archiver["obj"].entity is mock_archiver["mock_dialog"].entity
    assert mock_archiver["obj"].config is mock_archiver["mock_config"]
    assert mock_archiver["obj"].id == 1
    assert mock_archiver["obj"].type == "Something"
    assert mock_archiver["obj"].total_messages == 10
    assert mock_archiver["mock_logger"].call_count == 2
    assert mock_archiver["mock_logger"].call_args_list == [
        call("Initiating the dialog class (the synchronous part)..."),
        call("Initiating the dialog class (the asynchronous part)..."),
    ]
    mock_archiver["mock_get_id"].assert_called_once_with(
        mock_archiver["mock_dialog"].entity
    )

    mock_archiver["mock_get_type"].assert_called_once()

    mock_archiver["mock_get_session"].assert_called_once()
    assert mock_archiver["obj"].session is mock_archiver["mock_session"]

    new_dialog = mock_archiver["mock_db_dialog"](
        dialog_id=1, name="Me", type="Something"
    )
    mock_archiver["mock_session"].add.assert_called_once_with(new_dialog)
    mock_archiver["mock_session"].flush.assert_called_once()
    mock_archiver["mock_session"].query.asssert_called_once_with(
        mock_archiver["mock_db_dialog"]
    )

    mock_archiver["mock_client"].get_messages.assert_awaited_once_with(
        mock_archiver["mock_dialog"], limit=0
    )
    mock_archiver["mock_progress"].assert_called_once_with(10, "Me")
    mock_archiver["mock_file"].assert_called_once_with(5)
    mock_archiver["mock_error"].assert_called_once_with(
        mock_archiver["progress"],
        mock_archiver["obj"],
    )
    mock_archiver["mock_checkpoint"].assert_called_once()
    mock_archiver["progress"].use_checkpoint.assert_called_once_with([123])
    mock_archiver["obj"].users = set()


def test_dialog_get_type_with_user(mock_archiver):
    obj = mock_archiver["obj"]
    entity = MagicMock(spec=types.User)
    obj.entity = entity
    assert obj.get_dialog_type() == "User"


def test_dialog_get_type_with_chat(mock_archiver):
    obj = mock_archiver["obj"]
    entity = MagicMock(spec=types.Chat)
    obj.entity = entity
    assert obj.get_dialog_type() == "Chat"


def test_dialog_get_type_with_channel(mock_archiver):
    obj = mock_archiver["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = True
    obj.entity = entity
    assert obj.get_dialog_type() == "Channel"


def test_dialog_get_type_with_supergroup(mock_archiver):
    # .megagroup
    obj = mock_archiver["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = False
    obj.entity = entity
    assert obj.get_dialog_type() == "Supergroup"


def test_dialog_get_type_with_unknown(mock_archiver):
    obj = mock_archiver["obj"]
    entity = MagicMock()
    obj.entity = entity
    assert obj.get_dialog_type() == "Unknown"


@patch("objects.archiver.Archiver.get_checkpoint")
@patch("time.perf_counter")
def test_dialog_save_checkpoint(
    mock_counter, mock_get_checkpoint, mock_archiver, mock_session
):
    obj = mock_archiver["obj"]
    progress = mock_archiver["progress"]

    progress.last_message_id = 33
    progress.message_counter = 3

    mock_counter.return_value = 3.3
    progress.time_start = 3.1

    obj.session = mock_session

    mock_get_checkpoint.return_value = (None, None, 0.0)
    mock_session.add(Dialog(dialog_id=1, type="Anything"))

    obj.save_checkpoint()

    result = mock_session.query(
        Dialog.dialog_id,
        Dialog.last_message_id,
        Dialog.message_counter,
        Dialog.archiving_time,
    ).one()

    # Python floating point precision makes it so it's not 0.2
    assert (1, 33, 3, 0.19999999999999973) == result
    mock_get_checkpoint.assert_called_once()
    mock_counter.assert_called_once()


def test_dialog_get_checkpoint_with_empty_entry(mock_archiver, mock_session):
    obj = mock_archiver["obj"]
    obj.session = mock_session
    mock_session.add(Dialog(dialog_id=1, type="Anything"))

    assert obj.get_checkpoint() == (1, 0.0, 0.0)


def test_dialog_get_checkpoint_with_one_entry(mock_archiver, mock_session):
    obj = mock_archiver["obj"]
    obj.session = mock_session

    new_dialog = Dialog(
        dialog_id=1,
        type="Anything",
        last_message_id=33,
        message_counter=3,
        archiving_time=3.3,
    )
    mock_session.add(new_dialog)

    assert obj.get_checkpoint() == (33, 3, 3.3)


def test_dialog_get_checkpoint_with_many_entries(mock_archiver, mock_session):
    obj = mock_archiver["obj"]
    obj.session = mock_session

    new_dialog1 = Dialog(
        dialog_id=1,
        type="Anything",
        last_message_id=33,
        message_counter=3,
        archiving_time=3.3,
    )
    mock_session.add(new_dialog1)

    new_dialog2 = Dialog(dialog_id=2, type="Anything")
    mock_session.add(new_dialog2)

    assert obj.get_checkpoint() == (33, 3, 3.3)


@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
def test_dialog_key_interruption_with_no_user_info(
    mock_insert, mock_save, mock_archiver, capsys
):
    obj = mock_archiver["obj"]

    session = mock_archiver["mock_session"]

    config = mock_archiver["mock_config"]
    config.user_info = False

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()
    mock_insert.assert_not_called()

    # one call in setup
    assert session.commit.call_count == 2
    session.close.assert_called_once()


@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
def test_dialog_key_interruption_with_one_user(
    mock_insert, mock_save, mock_archiver, capsys
):
    obj = mock_archiver["obj"]
    obj.users = {1}

    session = mock_archiver["mock_session"]

    config = mock_archiver["mock_config"]
    config.user_info = True

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()
    mock_insert.assert_called_once_with(mock_archiver["mock_session"], 1, 1)

    # one call in setup
    assert session.commit.call_count == 2
    session.close.assert_called_once()


@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
def test_dialog_key_interruption_with_many_users(
    mock_insert, mock_save, mock_archiver, capsys
):
    obj = mock_archiver["obj"]
    obj.users = {1, 2}

    session = mock_archiver["mock_session"]

    config = mock_archiver["mock_config"]
    config.user_info = True

    obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()

    assert mock_insert.call_count == 2
    assert mock_insert.call_args_list == [
        call(mock_archiver["mock_session"], 1, 1),
        call(mock_archiver["mock_session"], 2, 1),
    ]

    # one call in setup
    assert session.commit.call_count == 2
    session.close.assert_called_once()


@pytest.mark.asyncio
@patch("objects.archiver.user_id_handler")
@patch("objects.archiver.forward_handler")
@patch("objects.archiver.reply_handler")
@patch("objects.archiver.text_handler")
@patch("objects.archiver.reaction_handler", new_callable=AsyncMock)
@patch("objects.archiver.stickers_handler", new_callable=AsyncMock)
async def test_dialog_archive_message(
    mock_stickers,
    mock_reaction,
    mock_text,
    mock_reply,
    mock_forward,
    mock_user,
    mock_archiver,
    mock_session,
):
    obj = mock_archiver["obj"]
    config = mock_archiver["mock_config"]
    file = mock_archiver["file"]
    progress = mock_archiver["progress"]

    message = MagicMock()
    message.id = 33
    message.views = 600
    message.file = MagicMock()
    message.file.size = 100
    message.file.sticker_set = "Just a str for testing, not important"

    DATES = date_consts()
    message.date = DATES[1]
    message.edit_date = DATES[2]

    config.texts = True
    config.files = True
    config.reactions = True

    file.handle = AsyncMock()
    file.handle.return_value = ["There", "Name", "Secret", 3.0, 1]

    progress.used_space_in_MB = 25

    obj.session = mock_session

    mock_user.return_value = ["Me", 5]
    mock_forward.return_value = ["He", 17]
    mock_reply.return_value = (32, 0, "Noice")
    mock_text.return_value = "Noice day"

    await obj.archive_message(message)

    mock_user.assert_called_once_with(message, obj.users)
    mock_forward.assert_called_once_with(message, obj.users)
    mock_reply.assert_called_once_with(message, obj.users)
    mock_text.assert_called_once_with(message)

    file.handle.assert_awaited_once_with(message)
    mock_stickers.assert_awaited_once_with(
        mock_archiver["mock_client"],
        message,
        1,
        mock_session,
    )
    assert progress.used_space_in_MB == 25

    mock_reaction.assert_awaited_once_with(
        mock_archiver["mock_client"],
        mock_archiver["mock_dialog"],
        message,
        mock_session,
    )

    result = mock_session.query(
        Message.id,
        Message.dialog_id,
        Message.message_id,
        Message.author_name,
        Message.views,
        Message.sender_id,
        Message.forward_from_username,
        Message.forward_from_user_id,
        Message.replied_to_id,
        Message.replied_to_entity_id,
        Message.replied_to_text,
        Message.text,
        Message.date,
        Message.edit_date,
        Message.file_path,
        Message.file_name,
        Message.file_id,
        Message.file_size,
        Message.downloaded_file,
    ).one()

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
        0,
        "Noice",
        "Noice day",
        DATES[1],
        DATES[2],
        "There",
        "Name",
        "Secret",
        3.0,
        1,
    ) == result
