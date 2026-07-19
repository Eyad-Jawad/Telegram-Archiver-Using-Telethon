from objects import errors
from unittest.mock import MagicMock, AsyncMock, patch, call
from telethon.errors import FloodWaitError
import pytest


@pytest.fixture
def mockErr():
    id = 1
    conn = MagicMock()
    cursor = MagicMock()
    progress = MagicMock()
    fileHanlder = MagicMock()
    dialogObject = MagicMock()

    progress.lastMessageID = 5

    err = errors.Errors(id, conn, cursor, progress, fileHanlder, dialogObject)

    return err


def testErrorClassAttributes():
    id = 1
    conn = MagicMock()
    cursor = MagicMock()
    progress = MagicMock()
    fileHanlder = MagicMock()
    dialogObject = MagicMock()

    err = errors.Errors(id, conn, cursor, progress, fileHanlder, dialogObject)

    assert err.id is id
    assert err.conn is conn
    assert err.cursor is cursor
    assert err.progressClass is progress
    assert err.fileClass is fileHanlder
    assert err.dialogObject is dialogObject


@pytest.mark.asyncio
async def testErrorClassWithNormalError(comesFrom, mockErr, capsys):
    err = MagicMock(spec=RuntimeError("Err"))
    err.__str__.return_value = "Error"

    await mockErr.handle(err, comesFrom)

    captured = capsys.readouterr()
    assert captured.out == "Error occurred: Error\nProgress\n"

    mockErr.dialogObject.saveCheckpoint.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def testErrorClassWithNormalError(mockSleep, mockErr):
    err = MagicMock(spec=FloodWaitError)
    err.__str__.return_value = "Error"
    err.seconds = 10

    await mockErr.handle(err)

    mockErr.dialogObject.saveCheckpoint.assert_called_once()

    mockSleep.assert_awaited_once_with(10)
