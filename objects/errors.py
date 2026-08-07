import asyncio
import logging

from telethon.errors import FloodWaitError

from .progress import Progress

logger = logging.getLogger(__name__)


class Errors:
    def __init__(
        self,
        progress: Progress,
        archiver,
    ) -> None:
        """
        Initialize the Errors class.

        Args:
            progress (objects.progress.Progress):
                The progress object for the program, used to access
                updated last_message_id to log in caes of an error.

            archiver (objects.archiver.Archiver):
                The archiver object of the program, used to save
                a checkpoint in case of an error.
        """
        logger.info("Setting up the Errors class...")
        self.progress = progress
        self.archiver = archiver

    async def handle(self, error) -> None:
        """
        A method that saves the current progress, logs the error, and
        solves it in case it is a FloodWaitError.

        Args:
            error:
                the error caught by the try except statement.
        """

        # Save the progress
        await self.archiver.save_checkpoint()

        logger.error(f"Error occurred: {error}.")
        logger.error(
            f"Error occurred at message {self.progress.last_message_id}."
        )

        # If the error is a FloodWaitError, simply wait.
        if isinstance(error, FloodWaitError):
            logger.warning(f"You have been rate limited for {error.seconds}.")
            await asyncio.sleep(error.seconds)
