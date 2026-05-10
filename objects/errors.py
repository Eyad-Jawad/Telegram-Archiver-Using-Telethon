import asyncio
from . import file, progress
from helpers.utils import saveCheckpoint, clearLastLine
from telethon.errors import FloodWaitError

class Errors:
    def __init__(
            self, 
            path: str, 
            progress: progress.Progress, 
            fileHanlder: file.File
        ) -> None:
        
        self.path           = path
        self.progressClass  = progress
        self.fileClass      = fileHanlder
    
    async def handle(self, error) -> None:
        saveCheckpoint(
            self.progressClass.lastMessageID, 
            self.progressClass.messageCounter,
            self.fileClass.counter,
            self.progressClass.savedDialogInfo,
            self.path,
            self.progressClass.timeStart
        )

        self.fileClass.emptyBigFilesLog()

        with open(f"{self.path}/errors.txt", 'a') as f:
            f.write(
                f"Error occured: "
                f"at message {self.progressClass.lastMessageID}:\n"
                f"{error}\n\n"
            )

        if isinstance(error, FloodWaitError):
            print(f"You've been rate limited for {error.seconds}s")
            await asyncio.sleep(error.seconds)
            clearLastLine()