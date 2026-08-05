from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.errors import FloodWaitError

from objects.errors import Errors


@pytest.fixture
def mock_error():
    conn = MagicMock()
    progress = MagicMock()
    archiver = MagicMock()

    progress.last_message_id = 5

    err = Errors(conn, progress, archiver)

    return err


def test_error_class_attributes():
    conn = MagicMock()
    progress = MagicMock()
    archiver = MagicMock()

    err = Errors(conn, progress, archiver)

    assert err.conn is conn
    assert err.progress is progress
    assert err.archiver is archiver


@pytest.mark.asyncio
async def test_error_class_with_normal_error(mock_error):
    err = MagicMock(spec=RuntimeError("Err"))
    err.__str__.return_value = "Error"

    await mock_error.handle(err)

    mock_error.archiver.save_checkpoint.assert_called_once()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_error_class_with_FloodWaitError_error(mock_sleep, mock_error):
    err = MagicMock(spec=FloodWaitError)
    err.__str__.return_value = "Error"
    err.seconds = 10

    await mock_error.handle(err)

    mock_error.archiver.save_checkpoint.assert_called_once()

    mock_sleep.assert_awaited_once_with(10)
