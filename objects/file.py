from telethon import custom
import logging

logger = logging.getLogger(__name__)


class File:
    def __init__(self, sizeThreshold: int) -> None:
        logger.info("Setting up the File class...")
        self.sizeThreshold: int = sizeThreshold  # in bytes
        self.PATH: str = "Media/"

    async def handle(self, message: custom.message.Message) -> list[int | float]:
        try:
            if not message or not message.file:
                return [
                    0,  # File Path
                    0.0,  # File ID
                    0,  # File size
                    0,  # Big file (flag)
                ]

            file = message.file

            fileId = None
            if message.photo:
                fileId = message.photo.id
            else:
                fileId = file.id

            # if the file is withing the threshold, download it
            if file.size < self.sizeThreshold:
                filePath = await message.download_media(file=self.PATH)

                return [filePath, fileId, byteToMB(file.size), 0]

            return [0, fileId, byteToMB(file.size), 1]

        except Exception as e:
            logger.exception(f"Exception occurred : {e}")

        return [0, 0.0, 0, 0]


def byteToMB(size: int):
    return (size / 1024) / 1024
