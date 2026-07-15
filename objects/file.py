from telethon import custom


class File:
    def __init__(self, sizeThreshold: int) -> None:
        self.sizeThreshold: int = sizeThreshold  # in bytes
        self.PATH: str = "Media/"

    async def handle(self, message: custom.message.Message) -> list[int]:
        if not message or not message.file:
            return [
                0, # File Path
                0, # File ID
                0, # Big file (flag)
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

            return [filePath, fileId, 0]

        return [0, fileId, 1]