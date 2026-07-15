import asyncio, sqlite3
from . import file, progress, dialog
from helpers.utils import clearLastLine
from telethon.errors import FloodWaitError


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

        self.id = id
        self.conn = conn
        self.cursor = cursor
        self.progressClass = progress
        self.fileClass = fileHanlder
        self.dialogObject = dialogObject

    async def handle(self, error, comesFrom: str | None = None) -> None:
        self.dialogObject.saveCheckpoint()

        print(f"Error occurred: {error}")

        self.conn.commit()

        with open("errors.txt", "a") as f:
            f.write(
                f"Error occurred: "
                f"at message {self.progressClass.lastMessageID}:\n"
                f"{error}\n"
            )

            if comesFrom:
                f.write(f"This error was raised from {comesFrom} function\n\n")

        if isinstance(error, FloodWaitError):
            print(f"You've been rate limited for {error.seconds}s")
            await asyncio.sleep(error.seconds)
            clearLastLine()
