import asyncio
import sqlite3
import logging
from .progress import Progress
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)


class Errors:
    def __init__(
        self,
        conn: sqlite3.Connection,
        progress: Progress,
        dialog,
    ) -> None:
        """
        Initialize the Errors class.

        Args:
            conn (sqlite3.Connection):
                The connection object to the sqlite3 database,
                used to commit in caes of an error.

            progress (objects.progress.Progress):
                The progress object for the program, used to access
                updated last_message_id to log in caes of an error.

            dialog (objects.dialog.Dialog):
                The dialog object of the program, used to save
                a checkpoint in case of an error.
        """
        logger.info("Setting up the Errors class...")
        self.conn = conn
        self.progress = progress
        self.dialog = dialog

    async def handle(self, error) -> None:
        """
        A method that saves the current progress, logs the error, and
        solves it in case it is a FloodWaitError.

        Args:
            error:
                the error caught by the try except statement.
        """

        # Save the progress
        self.dialog.save_checkpoint()

        self.conn.commit()

        logger.error(f"Error occurred: {error}.")
        logger.error(f"Error occurred at message {self.progress.last_message_id}.")

        # If the error is a FloodWaitError, simply wait.
        if isinstance(error, FloodWaitError):
            logger.warning(f"You have been rate limited for {error.seconds}.")
            await asyncio.sleep(error.seconds)
