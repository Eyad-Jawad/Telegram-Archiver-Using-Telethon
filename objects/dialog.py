import asyncio, os, csv
from telethon import types, utils
from telethon.errors import FloodWaitError

import helpers
from .errors import Errors as err
from .file import File as file
from .config import Config as con
from .progress import Progress as prog


class Dialog:
    # client, config, dialog
    def __init__(self, client, config: con, dialog) -> None:
        self.dialog = dialog
        self.entity = dialog.entity
        self.config: con = config
        self.client = client

        self.id: int = utils.get_peer_id(dialog.entity)
        self.type: str = self.getDialogType()
        self.path: str = f"dialogs/{self.type}/{self.id}"

        try:
            os.makedirs(f"{self.path}", exist_ok=True)
            os.makedirs(f"{self.path}/files", exist_ok=True)
        except OSError as e:
            print(f"Error: {e} occurred.")

    async def setUp(self):
        self.totalMessages: int = (
            await self.client.get_messages(self.dialog, limit=0)
        ).total

        self.progress: prog = prog(self.totalMessages)

        self.file: file = file(self.path, self.config.fileSizeThresholdInBytes)

        self.error: err = err(self.path, self.progress, self.file)

        self.users = set()

        checkpoint: list = helpers.utils.getCheckpoint(self.path)
        self.file.useCheckpoint(checkpoint)
        self.progress.useCheckpoint(checkpoint)

    def getDialogType(self) -> str:
        if isinstance(self.entity, types.User):
            return "User"
        elif isinstance(self.entity, types.Chat):
            return "Chat"
        elif isinstance(self.entity, types.Channel):
            if self.entity.broadcast:
                return "Channel"
            else:
                return "Supergroup"
        else:
            return "Unknown"

    async def archive(self) -> None:
        textPipeFunctions: list = [
            helpers.text.forwardHandler,
            helpers.text.replyHandler,
            helpers.text.textHandler,
        ]

        print(self.progress)

        try:
            with open(f"{self.path}/TextMessages.csv", "a") as texts, open(
                f"{self.path}/Reactions.csv", "a"
            ) as reactions:
                CSVMessagesWrtier = csv.writer(texts)
                CSVReactionsWriter = csv.writer(reactions)

                secondCol = (
                    "Sender ID" if self.getDialogType() != "Channel" else "Author Name"
                )
                CSVMessagesWrtier.writerow(
                    [
                        "Message Id",
                        secondCol,
                        "Forward From username",
                        "Forward From user Id",
                        "Replyed-To Ids",
                        "Text",
                        "Date",
                        "File Id",
                        "File Relative Id",
                        "Donwloaded Media",
                    ]
                )
                if self.getDialogType() == "Channel":
                    CSVReactionsWriter.writerow(["Message Id", "Reaction", "Count"])
                else:
                    CSVReactionsWriter.writerow(
                        ["Message Id", "Reactor Id", "Date Of Reacting", "Reaction"]
                    )

                async for message in self.client.iter_messages(
                    self.dialog.entity,
                    reverse=True,
                    offset_id=self.progress.lastMessageID,
                ):
                    # for writing into the file at once
                    messagesRow = [0] * 10
                    messagesRow[0] = message.id
                    messagesRow[6] = message.date

                    if self.config.texts:
                        for function in textPipeFunctions:
                            await function(message, messagesRow, self.users)
                        messagesRow[1] = helpers.info.userIdHandler(message, self.users)

                    if self.config.files and message.file:
                        await self.file.handle(message, messagesRow)
                        self.progress.sizeInMb += (
                            message.file.size / self.progress.MbToByte
                        )

                    if self.config.reactions:
                        await helpers.reactions.reactionHandler(
                            self.client, self.dialog, message, CSVReactionsWriter
                        )

                    CSVMessagesWrtier.writerow(messagesRow)
                    self.progress.update(message.id)

                if self.config.dialogInfo and not self.progress.savedDialogInfo:
                    await helpers.info.getGroupOrChannelInfo(
                        self.client, self.dialog, self.path, self.users, self.error
                    )
                    self.progress.savedDialogInfo = True

                if self.config.userInfo:
                    await helpers.info.usersHandler(
                        self.client, self.users, self.path, self.error
                    )

                if self.config.files:
                    self.file.emptyBigFilesLog()

                helpers.utils.saveCheckpoint(
                    self.progress.lastMessageID,
                    self.progress.messageCounter,
                    self.file.counter,
                    self.progress.savedDialogInfo,
                    self.path,
                    self.progress.timeStart,
                )
                helpers.utils.clearLastLine(3)
                print(f"Done archiving {self.dialog.name}!")

        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            helpers.utils.clearLastLine(3)
            print("Please wait a moment while the saving the checkpoint")

            self.file.emptyBigFilesLog()

            helpers.saveCheckpoint(
                self.progress.lastMessageID,
                self.progress.messageCounter,
                self.file.counter,
                self.progress.savedDialogInfo,
                self.path,
                self.progress.timeStart,
            )

            if self.config.userInfo:
                with open(f"{self.path}/Users.csv", "w") as f:
                    CSVUserWriter = csv.writer(f)
                    CSVUserWriter.writerow(["User Id"])
                    for user in self.users:
                        CSVUserWriter.writerow([user])

            helpers.clearLastLine()
            print("Done!")
            exit(0)

        except Exception as e:
            await self.error.handle(e, self.archive)

    async def calculateDialogSpace(self):
        self.progress: prog = prog(self.dialog)

        try:
            self.progress.print()

            async for message in self.client.iter_messages(self.dialog.entity):
                self.progress.messageCounter += 1
                self.progress.checkProgress()

                if (
                    message.file
                    and message.file.size < self.config.fileSizeThresholdInBytes
                ):
                    self.progress.sizeInMb += message.file.size / self.progress.MbToByte

            helpers.clearLastLine(3)
            print(
                f"Dialog {self.dialog.title} will take about {self.progress.sizeInMb:.3f}MB"
            )
            return self.progress.sizeInMb

        except FloodWaitError as e:
            print(f"You've been rate limited for {e.seconds}s")
            await asyncio.sleep(e.seconds)
