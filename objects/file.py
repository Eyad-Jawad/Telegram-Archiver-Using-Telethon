import logging

from telethon import custom

from helpers.local_utils import byte_to_mb
from db.models import Message

logger = logging.getLogger(__name__)


class File:
    def __init__(self, size_threshold: float) -> None:
        """
        Initialize the File class object

        Args:
            size_threshold (float):
                The maximum size of the files to download of which any larger
                will be ignored, parsed by the config class from user in CLI args.
        """

        logger.debug("Setting up the File class...")

        self.size_threshold = size_threshold  # in bytes
        self.PATH = "Media/"

    async def handle(
        self,
        tel_msg: custom.message.Message,
        db_msg: Message,
    ) -> None:
        """
        A method that handles downloading a file, and getting its metadata.

        Args:
            message (telethon.custom.message.Message):
                A telegram dialog's message provided by telethon.

        db_msg (db.models.Message):
            The database orm object that holds the data and will
            be appended into the database.
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
            if file.size < self.size_threshold:
                file_path = await tel_msg.download_media(file=self.PATH)

                db_msg.file_path = file_path
                db_msg.downloaded_file = True

                return

            # Did not download the file, return
            return

        except Exception:
            logger.exception(f"Exception occurred at message {tel_msg.id}")
            return
