import logging
from telethon import custom
from helpers.local_utils import byte_to_MB

logger = logging.getLogger(__name__)


class File:
    def __init__(self, size_threshold: int) -> None:
        """
        Initialize the File class object

        Args:
            size_threshold (int):
                The maximum size of the files to download of which any larger
                will be ignored, parsed by the config class from user in CLI args.
        """

        logger.info("Setting up the File class...")

        self.size_threshold = size_threshold  # in bytes
        self.PATH = "Media/"

    async def handle(
        self, message: custom.message.Message
    ) -> tuple[str, str, float, bool]:
        """
        A method that handles downloading a file, and getting its metadata.

        Args:
            message (telethon.custom.message.Message):
                A telegram dialog's message provided by telethon.

        Returns:
            Tuple: [
                str (File path, if downloaded, else empty),
                str (File id, id there's any, else emtpy),
                float (File size in megabytes, if there's any, else 0.0),
                bool (Downloaded file, True for yes and False for no, which can
                be because the file exceeds the size_threshold, or because there's no file)
            ]
        """
        try:
            # If there's not message (safety), or the message
            # does not have a file, return empty inputs
            if not message or not message.file:
                return (
                    "",  # File path
                    "",  # File id
                    0.0,  # File size
                    False,  # Downloaded file (flag)
                )

            file = message.file

            file_id = None

            # Telethon or telegram internal thing, photos and files are alike,
            # but to get a photo's id is different from getting a file's id.
            if message.photo:
                file_id = message.photo.id
            else:
                file_id = file.id

            # If the file is withing the threshold, download it
            if file.size < self.size_threshold:
                file_path = await message.download_media(file=self.PATH)

                return (file_path, file_id, byte_to_MB(file.size), True)

            # Did not download the file, return the metadata only
            return ("", file_id, byte_to_MB(file.size), False)

        except Exception as e:
            logger.exception(f"Exception occurred : {e}")
            return ("", "", 0.0, False)
