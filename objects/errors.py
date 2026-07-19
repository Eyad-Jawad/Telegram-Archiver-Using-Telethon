import asyncio, sqlite3, logging
from . import file, progress, dialog
from helpers.utils import clearLastLine
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


class Errors:
    def __init__(
        self,
        id: int,
        conn: sqlite3.Connection,
        cursor: sqlite3.Cursor,
        progress: progress.Progress,
        fileHanlder: file.File,
        dialogObject: dialog.Dialog,
    ) -> None:
        logger.info("Setting up the Errors class...")
        self.id = id
        self.conn = conn
        self.cursor = cursor
        self.progressClass = progress
        self.fileClass = fileHanlder
        self.dialogObject = dialogObject

    async def handle(self, error) -> None:
        self.dialogObject.saveCheckpoint()

        self.conn.commit()

        logger.error(f"Error occurred: {error}.")
        logger.error(f"Error occurred at message {self.progressClass.lastMessageID}.")

        if isinstance(error, FloodWaitError):
            logger.warning(f"You have been rate limited for {error.seconds}.")
            await asyncio.sleep(error.seconds)
