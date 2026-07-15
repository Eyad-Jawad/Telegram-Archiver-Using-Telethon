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
@patch("builtins.open")
@pytest.mark.parametrize(
    ("comesFrom, writeCallCount, writeArgList"),
    [
        (
            "Me",
            2,
            [
                call("Error occurred: at message 5:\nError\n"),
                call("This error was raised from Me function\n\n"),
            ],
        ),
        (None, 1, [call("Error occurred: at message 5:\nError\n")]),
    ],
)
async def testErrorClassWithNormalError(
    mockOpen, writeCallCount, comesFrom, writeArgList, mockErr, capsys
):
    err = MagicMock(spec=RuntimeError("Err"))
    err.__str__.return_value = "Error"

    file = MagicMock()
    mockOpen.return_value.__enter__.return_value = file

    await mockErr.handle(err, comesFrom)

    captured = capsys.readouterr()
    assert captured.out == "Error occurred: Error\nProgress\n"

    mockErr.dialogObject.saveCheckpoint.assert_called_once()
    mockOpen.assert_called_once_with("errors.txt", "a")
    assert file.write.call_count == writeCallCount
    assert file.write.call_args_list == writeArgList


@pytest.mark.asyncio
@patch("builtins.open")
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("objects.errors.clearLastLine")
async def testErrorClassWithNormalError(
    mockClearLine, mockSleep, mockOpen, mockErr, capsys
):
    err = MagicMock(spec=FloodWaitError)
    err.__str__.return_value = "Error"
    err.seconds = 10

    file = MagicMock()
    mockOpen.return_value.__enter__.return_value = file

    await mockErr.handle(err)
    captured = capsys.readouterr()

    mockErr.dialogObject.saveCheckpoint.assert_called_once()
    mockOpen.assert_called_once()
    file.write.assert_called_once()

    assert captured.out == "Error occurred: Error\nYou've been rate limited for 10s\n"
    mockSleep.assert_awaited_once_with(10)
    mockClearLine.assert_called_once()
