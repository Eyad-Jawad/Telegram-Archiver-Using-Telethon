from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch
from types import SimpleNamespace

import pytest
import pytest_asyncio
from telethon import types
from sqlalchemy import select, update

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
@patch("objects.archiver.Archiver.get_checkpoint", new_callable=AsyncMock)
@patch("objects.archiver.file")
@patch("objects.archiver.prog")
@patch("objects.archiver.err")
@patch("objects.archiver.get_session")
@patch("objects.archiver.Archiver.get_dialog_type")
@patch("telethon.utils.get_peer_id")
async def mock_archiver(
    mock_get_id,
    mock_get_type,
    mock_get_session,
    mock_error,
    mock_progress,
    mock_file,
    mock_checkpoint,
    mock_client,
    mock_dialog,
    mock_config,
    mock_session,
):
    progress = MagicMock()
    file = MagicMock()
    error = MagicMock()

    mock_get_id.return_value = 1
    mock_get_type.return_value = "Something"

    mock_error.return_value = error
    mock_progress.return_value = progress
    mock_file.return_value = file

    mock_get_session.return_value = mock_session

    mock_checkpoint.return_value = [123]

    obj = Archiver(mock_client, mock_config, mock_dialog)
    await obj.set_up()

    return SimpleNamespace(
        obj=obj,
        mock_dialog=mock_dialog,
        mock_client=mock_client,
        mock_config=mock_config,
        mock_get_id=mock_get_id,
        mock_get_type=mock_get_type,
        mock_get_session=mock_get_session,
        mock_session=mock_session,
        mock_progress=mock_progress,
        progress=progress,
        mock_file=mock_file,
        file=file,
        mock_error=mock_error,
        mock_checkpoint=mock_checkpoint,
    )

@pytest.mark.asyncio
async def test_dialog_init(mock_archiver):
    arc = mock_archiver
    
    assert arc.obj.client is arc.mock_client
    assert arc.obj.dialog is arc.mock_dialog
    assert arc.obj.entity is arc.mock_dialog.entity

    assert arc.obj.id == 1
    arc.mock_get_id.assert_called_once_with(
        arc.mock_dialog.entity
    )

    assert arc.obj.type == "Something"
    arc.mock_get_type.assert_called_once()

    assert arc.obj.config is arc.mock_config
    
    assert arc.obj.total_messages == 10

    assert arc.obj.session is arc.mock_session
    arc.mock_get_session.assert_called_once()

    query = await arc.mock_session.execute(select(Dialog))
    query = query.scalar_one()

    assert query.dialog_id == 1
    assert query.type == "Something"
    assert query.name == "Me"
    assert query.total_number_of_messages == 10
    assert query.last_message_id == 1
    assert query.message_counter == 0
    assert query.archiving_time == 0.0

    arc.mock_client.get_messages.assert_awaited_once_with(
        arc.mock_dialog, limit=0
    )
    arc.mock_progress.assert_called_once_with(10, "Me")
    arc.mock_file.assert_called_once_with(5)
    arc.mock_error.assert_called_once_with(
        arc.progress,
        arc.obj,
    )

    arc.mock_checkpoint.assert_awaited_once()
    arc.progress.use_checkpoint.assert_called_once_with([123])

    assert arc.obj.users == set()


def test_dialog_get_type_with_user(mock_archiver):
    obj = mock_archiver.obj
    entity = MagicMock(spec=types.User)
    obj.entity = entity
    assert obj.get_dialog_type() == "User"


def test_dialog_get_type_with_chat(mock_archiver):
    obj = mock_archiver.obj
    entity = MagicMock(spec=types.Chat)
    obj.entity = entity
    assert obj.get_dialog_type() == "Chat"


def test_dialog_get_type_with_channel(mock_archiver):
    obj = mock_archiver.obj
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = True
    obj.entity = entity
    assert obj.get_dialog_type() == "Channel"


def test_dialog_get_type_with_supergroup(mock_archiver):
    # .megagroup
    obj = mock_archiver.obj
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = False
    obj.entity = entity
    assert obj.get_dialog_type() == "Supergroup"


def test_dialog_get_type_with_unknown(mock_archiver):
    obj = mock_archiver.obj
    entity = MagicMock()
    obj.entity = entity
    assert obj.get_dialog_type() == "Unknown"


@pytest.mark.asyncio
@patch("objects.archiver.Archiver.get_checkpoint")
@patch("time.perf_counter")
async def test_dialog_save_checkpoint(
    mock_counter, mock_get_checkpoint, mock_archiver, mock_session
):
    obj = mock_archiver.obj
    progress = mock_archiver.progress

    progress.last_message_id = 33
    progress.message_counter = 3

    mock_counter.return_value = 3.3
    progress.time_start = 3.1

    obj.session = mock_session

    mock_get_checkpoint.return_value = (None, None, 0.0)

    await obj.save_checkpoint()

    result = await mock_session.execute(select(Dialog))
    result = result.scalar_one()

    assert result.dialog_id == 1
    assert result.last_message_id == 33
    assert result.message_counter == 3
    # Python floating point precision makes it so it's not 0.2
    assert result.archiving_time == 0.19999999999999973

    mock_get_checkpoint.assert_called_once()
    mock_counter.assert_called_once()

@pytest.mark.asyncio
async def test_dialog_get_checkpoint_with_empty_entry(mock_archiver):
    obj = mock_archiver.obj

    assert await obj.get_checkpoint() == (1, 0.0, 0.0)

@pytest.mark.asyncio
async def test_dialog_get_checkpoint_with_one_entry(mock_archiver, mock_session):
    obj = mock_archiver.obj

    stmt = update(Dialog).values(
        last_message_id=33,
        message_counter=3,
        archiving_time=3.3,
    )

    await mock_session.execute(stmt)

    assert await obj.get_checkpoint() == (33, 3, 3.3)

@pytest.mark.asyncio
async def test_dialog_get_checkpoint_with_many_entries(mock_archiver, mock_session):
    obj = mock_archiver.obj
    obj.session = mock_session

    stmt = update(Dialog).values(
        last_message_id=33,
        message_counter=3,
        archiving_time=3.3,
    )

    await mock_session.execute(stmt)

    new_dialog2 = Dialog(dialog_id=2, type="Anything")
    mock_session.add(new_dialog2)

    assert await obj.get_checkpoint() == (33, 3, 3.3)

@pytest.mark.asyncio
@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
async def test_dialog_key_interruption_with_no_user_info(
    mock_insert, mock_save, mock_archiver, capsys,
):
    obj = mock_archiver.obj
    session = AsyncMock()
    obj.session = session

    config = mock_archiver.mock_config
    config.user_info = False

    await obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()
    mock_insert.assert_not_called()

    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()

@pytest.mark.asyncio
@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
async def test_dialog_key_interruption_with_one_user(
    mock_insert, mock_save, mock_archiver, capsys
):
    obj = mock_archiver.obj
    obj.users = {1}

    session = AsyncMock()
    obj.session = session

    config = mock_archiver.mock_config
    config.user_info = True

    await obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()
    mock_insert.assert_called_once_with(session, 1, 1)

    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()

@pytest.mark.asyncio
@patch("objects.archiver.Archiver.save_checkpoint")
@patch("objects.archiver.insert_users_ids")
async def test_dialog_key_interruption_with_many_users(
    mock_insert, mock_save, mock_archiver, capsys
):
    obj = mock_archiver.obj
    obj.users = {1, 2}

    session = AsyncMock()
    obj.session = session

    config = mock_archiver.mock_config
    config.user_info = True

    await obj.handle_key_interruption()

    capture = capsys.readouterr()
    assert (
        capture.out
        == "\nPlease wait a moment while the saving the checkpoint\n"
    )

    mock_save.assert_called_once()

    assert mock_insert.call_count == 2
    assert mock_insert.call_args_list == [
        call(session, 1, 1),
        call(session, 2, 1),
    ]

    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()


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
    obj = mock_archiver.obj
    config = mock_archiver.mock_config
    file = mock_archiver.file
    progress = mock_archiver.progress

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
        mock_archiver.mock_client,
        message,
        1,
        mock_session,
    )
    assert progress.used_space_in_MB == 25

    mock_reaction.assert_awaited_once_with(
        mock_archiver.mock_client,
        mock_archiver.mock_dialog,
        message,
        mock_session,
    )

    stmt = select(Message)
    result = await mock_session.execute(stmt)
    query = result.scalar_one()

    assert query.id == 1
    assert query.dialog_id == 1
    assert query.message_id == 33
    assert query.author_name == "Me"
    assert query.views == 600
    assert query.sender_id == 5
    assert query.forward_from_username == "He"
    assert query.forward_from_user_id == 17
    assert query.replied_to_id == 32
    assert query.replied_to_entity_id == 0
    assert query.replied_to_text == "Noice"
    assert query.text == "Noice day"
    assert query.date == DATES[1]
    assert query.edit_date == DATES[2]
    assert query.file_path == "There"
    assert query.file_name == "Name"
    assert query.file_id == "Secret"
    assert query.file_size == 3.0
    assert query.downloaded_file == 1