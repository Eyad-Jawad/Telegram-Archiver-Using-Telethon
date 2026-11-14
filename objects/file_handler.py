import logging
from collections.abc import Awaitable, Callable

from telethon import custom

from db.models import Message
from helpers.local_utils import byte_to_mb

from .progress import ProgressFileDelegation

logger = logging.getLogger(__name__)


def make_file_handler(
    size_threshold: float, prog_delegation: ProgressFileDelegation
) -> Callable[[custom.message.Message, Message], Awaitable[None]]:
    """
    A function that makes file handlers.
        prog_delegation (objects.progress.ProgressFileDelegation):
            An interface for the file to call update progress size
            without exposing anything unecessary.
    """

    logger.debug("Setting up the file handler closure...")

    path = "Media/"

    async def handle_file(
        tel_msg: custom.message.Message,
        db_msg: Message,
    ) -> None:
        """
        A function that handles downloading a file based on a threshold, and getting its metadata.
        """
        try:
            # If there's not message (safety), or the message
            # does not have a file, just return without setting anything
            if not tel_msg or not tel_msg.file:
                return

            file = tel_msg.file
            file_name = file.name or ""

            file_id = None

            # Telethon or telegram internal thing, photos and files are alike,
            # but to get a photo's id is different from getting a file's id.
            if tel_msg.photo:
                file_id = tel_msg.photo.id
            else:
                file_id = file.id

            db_msg.file_size = byte_to_mb(file.size)
            db_msg.file_name = file_name
            db_msg.file_id = file_id

            # If the file is within the threshold, download it
            if file.size <= size_threshold:
                file_path = await tel_msg.download_media(file=path)
                prog_delegation.update_file_progress(db_msg.file_size)

                logger.info(
                    f"Downloaded a {file.name} of size {db_msg.file_size:.4f}MB"
                )

                db_msg.file_path = file_path
                db_msg.downloaded_file = True

        except Exception:
            logger.exception(f"Exception occurred at message {tel_msg.id}")
            print("\n\n\nError\n\n\n")

    return handle_file
