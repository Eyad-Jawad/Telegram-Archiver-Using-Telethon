from unittest.mock import AsyncMock, MagicMock

import pytest

from objects.file import File


@pytest.fixture()
def file_class():
    return File(5)


def test_file_class_attributes(file_class):
    assert file_class.size_threshold == 5
    assert file_class.PATH == "Media/"


@pytest.mark.asyncio
async def test_file_handle_with_no_message(
    file_class, mock_message, check_db_msg_defaults
):
    await file_class.handle(None, mock_message)

    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_file_handle_with_no_file(
    file_class, mock_message, check_db_msg_defaults
):
    message = AsyncMock()
    message.file = None

    await file_class.handle(message, mock_message)

    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_file_handle_with_photo(
    file_class, mock_message, check_db_msg_defaults
):
    message = AsyncMock()
    file = MagicMock()
    photo = MagicMock()

    photo.id = "xyz"
    file.size = 4
    file.name = "Photo"
    message.photo = photo
    message.file = file

    message.download_media.return_value = "Somewhere"

    await file_class.handle(message, mock_message)

    await check_db_msg_defaults(
        mock_message,
        skips=(
            "file_path",
            "file_name",
            "file_id",
            "file_size",
            "downloaded_file",
        ),
    )
    assert mock_message.file_path == "Somewhere"
    assert mock_message.file_name == "Photo"
    assert mock_message.file_id == "xyz"
    assert mock_message.file_size == 3.814697265625e-06
    assert mock_message.downloaded_file == True

    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def test_file_handle_with_file(
    file_class, mock_message, check_db_msg_defaults
):
    message = AsyncMock()
    file = MagicMock()

    file.size = 2
    file.id = "zyx"
    file.name = "Big nose"
    message.photo = None
    message.file = file

    message.download_media.return_value = "There"

    await file_class.handle(message, mock_message)

    await check_db_msg_defaults(
        mock_message,
        skips=(
            "file_path",
            "file_name",
            "file_id",
            "file_size",
            "downloaded_file",
        ),
    )
    assert mock_message.file_path == "There"
    assert mock_message.file_name == "Big nose"
    assert mock_message.file_id == "zyx"
    assert mock_message.file_size == 1.9073486328125e-06
    assert mock_message.downloaded_file == True

    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def test_file_handle_with_big_file(
    file_class, mock_message, check_db_msg_defaults
):
    message = AsyncMock()
    file = MagicMock()

    file.size = 50
    file.id = "ijk"
    file.name = "Blueprint"
    message.photo = None
    message.file = file

    await file_class.handle(message, mock_message)

    await check_db_msg_defaults(
        mock_message,
        skips=(
            "file_name",
            "file_id",
            "file_size",
        ),
    )
    assert mock_message.file_name == "Blueprint"
    assert mock_message.file_id == "ijk"
    assert mock_message.file_size == 4.76837158203125e-05
