import pytest
from objects.file import File
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture()
def file_class():
    return File(5)


def test_file_class_attributes():
    file = File(5)

    assert file.size_threshold == 5
    assert file.PATH == "Media/"


@pytest.mark.asyncio
async def test_file_handle_with_no_message(file_class):
    assert await file_class.handle(None) == ("", "", 0.0, False)


@pytest.mark.asyncio
async def test_file_handle_with_no_file(file_class):
    message = AsyncMock()
    message.file = None
    assert await file_class.handle(message) == ("", "", 0.0, False)


@pytest.mark.asyncio
async def test_file_handle_with_photo(file_class):
    message = AsyncMock()
    file = MagicMock()
    photo = MagicMock()

    photo.id = "xyz"
    file.size = 4
    message.photo = photo
    message.file = file

    message.download_media.return_value = "Somewhere"

    assert await file_class.handle(message) == (
        "Somewhere",
        "xyz",
        3.814697265625e-06,
        True,
    )
    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def test_file_handle_with_file(file_class):
    message = AsyncMock()
    file = MagicMock()

    file.size = 2
    file.id = "zyx"
    message.photo = None
    message.file = file

    message.download_media.return_value = "There"

    assert await file_class.handle(message) == (
        "There",
        "zyx",
        1.9073486328125e-06,
        True,
    )
    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def test_file_handle_with_big_file(file_class):
    message = AsyncMock()
    file = MagicMock()

    file.size = 50
    file.id = "ijk"
    message.photo = None
    message.file = file

    assert await file_class.handle(message) == ("", "ijk", 4.76837158203125e-05, False)
