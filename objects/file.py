from telethon import custom


class File:
    def __init__(self, path: str, sizeThreshold: int) -> None:
        self.sizeThreshold: int = sizeThreshold  # in bytes
        self.counter: int = 1
        self.path: str = path + "/files"
        self.skippedStack: list[int] = []
        with open(f"{self.path}/bigfiles.csv", "w") as f:
            f.write("Message Id\n")

    def useCheckpoint(self, checkpoint: list) -> None:
        if not checkpoint:
            return
        self.counter = checkpoint[2]

    async def handle(self, message: custom.message.Message, messagesRow: list) -> None:
        file = message.file
        if not file:
            messagesRow[7] = 0  # File ID
            messagesRow[8] = 0  # File counter (relative ID)
            messagesRow[9] = 0  # Big file (flag)
            return

        if message.photo:
            messagesRow[7] = message.photo.id
        else:
            messagesRow[7] = file.id

        if file.size < self.sizeThreshold:
            messagesRow[8] = self.counter
            self.counter += 1

            messagesRow[9] = 0
            await self.downloadFiles(message)
            return

        # keep log of files not downloaded
        messagesRow[8] = 0
        messagesRow[9] = 1

        self.skippedStack.append(message.id)
        if len(self.skippedStack) >= 100:
            self.emptyBigFilesLog()

        return

    async def downloadFiles(self, message: custom.message.Message) -> None:
        file = message.file

        fileName = f"{self.counter} "

        if message.photo:
            fileName += ".jpg"
        elif file.name:
            fileName += file.name

        await message.download_media(file=f"{self.path}/{fileName}")

    def emptyBigFilesLog(self) -> None:
        with open(f"{self.path}/bigfiles.csv", "a") as f:
            while self.skippedStack:
                messageID: int = self.skippedStack.pop()
                f.write(f"{messageID}\n")
