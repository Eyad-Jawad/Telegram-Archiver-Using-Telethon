from objects import file as f
from unittest.mock import MagicMock, AsyncMock
import pytest


@pytest.fixture()
def fileClass():
    return f.File(5)


def testFileClassAttributes():
    file = f.File(5)

    assert file.sizeThreshold == 5
    assert file.PATH == "Media/"


@pytest.mark.asyncio
async def testFileHandleWithNoMessage(fileClass):
    assert await fileClass.handle(None) == [0, 0, 0]


@pytest.mark.asyncio
async def testFileHandleWithNoFile(fileClass):
    message = AsyncMock()
    message.file = None
    assert await fileClass.handle(message) == [0, 0, 0]


@pytest.mark.asyncio
async def testFileHandleWithPhoto(fileClass):
    message = AsyncMock()
    file = MagicMock()
    photo = MagicMock()

    photo.id = 5
    file.size = 4
    message.photo = photo
    message.file = file

    message.download_media.return_value = "Somewhere"

    assert await fileClass.handle(message) == ["Somewhere", 5, 0]
    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def testFileHandleWithFile(fileClass):
    message = AsyncMock()
    file = MagicMock()

    file.size = 2
    file.id = 15
    message.photo = None
    message.file = file

    message.download_media.return_value = "There"

    assert await fileClass.handle(message) == ["There", 15, 0]
    message.download_media.assert_awaited_once_with(file="Media/")


@pytest.mark.asyncio
async def testFileHandleWithBigFile(fileClass):
    message = AsyncMock()
    file = MagicMock()

    file.size = 50
    file.id = 3
    message.photo = None
    message.file = file

    assert await fileClass.handle(message) == [0, 3, 1]
