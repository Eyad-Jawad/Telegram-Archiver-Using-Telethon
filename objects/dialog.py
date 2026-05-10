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
    def __init__(self, client, config, dialog):
        self.dialog = dialog
        self.entity = dialog.entity
        self.config = config
        self.client = client

        self.id = utils.get_peer_id(dialog.entity)
        self.type = self.getDialogType()
        self.path = f"dialogs/{self.type}/{self.id}"

        try:
            os.makedirs (f"{self.path}", exist_ok=True)
            os.makedirs (f"{self.path}/files", exist_ok=True)
        except OSError as e:
            print(f"Error: {e} occurred.")

    async def setUp(self):
        self.totalMessages: int = (
            await self.client.get_messages(
                self.dialog, 
                limit=0
            )
        ).total
        
        self.progress: prog = prog(self.totalMessages)

        self.file: file = file (
            self.path, 
            self.config.fileSizeThresholdInBytes
        )

        self.error: err = err(
            self.path, 
            self.progress, self.file
        )

        self.users = set()

        checkpoint: list = helpers.utils.getCheckpoint(self.path)
        self.file.useCheckpoint(checkpoint)
        self.progress.useCheckpoint(checkpoint)

    def getDialogType(self):
        if isinstance(self.entity, types.User):
            self.type = "User"
        elif isinstance(self.entity, types.Chat):
            self.type = "Chat"
        elif isinstance(self.entity, types.Channel):
            if self.entity.broadcast:
                self.type = "Channel"
            else:
                self.type = "Supergroup"
        else:
            self.type = "Unknown"
    
    async def archive(self, client, config: con):
        textPipeFunctions: list = [
            helpers.info.userIdHandler, 
            helpers.text.forwardHandler, 
            helpers.text.replyHandler, 
            helpers.text.textHandler
        ]
        
        print(self.progress)

        try: 
            with open(f"{self.path}/TextMessages.csv", 'a') as texts, \
                 open(f"{self.path}/Reactions.csv", 'a') as reactions:
                CSVMessagesWrtier  = csv.writer(texts)
                CSVReactionsWriter = csv.writer(reactions)

                async for message in client.iter_messages(
                    self.dialog.entity, 
                    reverse=True, 
                    offset_id=self.progress.lastMessageID
                ):
                    # for writing into the file at once
                    messagesRow    = [0] * 10
                    messagesRow[0] = message.id
                    messagesRow[6] = message.date

                    if config.texts:
                        for function in textPipeFunctions:
                            await function(message, messagesRow, self.users)

                    if config.files and message.file:
                        await self.file.handle(message, messagesRow)
                        self.progress.sizeInMb += message.file.size / self.progress.MbToByte

                    if config.reactions:
                        await helpers.reactions.reactionHandler(
                            client, 
                            self.dialog, 
                            message, 
                            CSVReactionsWriter
                        )

                    CSVMessagesWrtier.writerow(messagesRow)
                    self.progress.update(message.id)

                if config.dialogInfo and not self.progress.savedDialogInfo:
                    await helpers.info.getGroupOrChannelInfo(
                        self.dialog, 
                        self.path, 
                        self.users, 
                        self.error
                    )
                    self.progress.savedDialogInfo = True

                if config.userInfo:
                    await helpers.info.usersHandler(
                        self.user, 
                        self.path, 
                        self.error
                    )

                if config.files:
                    self.file.emptyBigFilesLog()

                helpers.utils.saveCheckpoint (
                    self.progress.lastMessageID, 
                    self.progress.messageCounter, 
                    self.file.counter, 
                    self.progress.savedDialogInfo, 
                    self.path, 
                    self.progress.timeStart
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
                self.progress.timeStart
            )

            if config.userInfo:
                with open(f"{self.path}/Users.csv", 'w') as f:
                    CSVUserWriter = csv.writer(f)
                    for user in self.user:
                        CSVUserWriter.writerow([user])

            helpers.clearLastLine()
            print("Done!")
            exit(0)

        except Exception as e:
            await self.error.handle(e)
    
    async def calculateDialogSpace(self, client, dialog, config: con):
        self.progress: prog = prog(dialog)

        try:
            self.progress.print()

            async for message in client.iter_messages(dialog.entity):
                self.progress.messageCounter += 1
                self.progress.checkProgress()
                
                if message.file and message.file.size < config.fileSizeThresholdInBytes:
                    self.progress.sizeInMb += message.file.size / self.progress.MbToByte

            helpers.clearLastLine(3)
            print(f"Dialog {dialog.title} will take about {self.progress.sizeInMb:.3f}MB")
            return self.progress.sizeInMb

        except FloodWaitError as e:
            print(f"You've been rate limited for {e.seconds}s")
            await asyncio.sleep(e.seconds)

