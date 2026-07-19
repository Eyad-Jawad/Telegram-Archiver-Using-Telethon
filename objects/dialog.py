import asyncio, sqlite3, time, logging
from telethon import types, utils, custom
from rich.live import Live

import helpers
from .errors import Errors as err
from .file import File as file
from .config import Config as con
from .progress import Progress as prog

logger = logging.getLogger(__name__)


class Dialog:
    # client, config, dialog
    def __init__(self, client, config: con, dialog) -> None:
        logger.info("Initiating the dialog class")
        self.conn = sqlite3.connect("telegram.db")
        self.cursor = self.conn.cursor()
        self.dialog = dialog
        self.entity = dialog.entity
        self.config: con = config
        self.client = client

        self.id: int = utils.get_peer_id(dialog.entity)
        self.type: str = self.getDialogType()

        helpers.sqlTables.makeTables(self.cursor)
        self.conn.commit()

        self.cursor.execute(
            "INSERT OR IGNORE INTO dialogs (dialogId, name, type) VALUES  (?, ?, ?)",
            [self.id, self.dialog.name, self.type],
        )

        self.conn.commit()

    async def setUp(self):
        self.totalMessages: int = (
            await self.client.get_messages(self.dialog, limit=0)
        ).total

        self.cursor.execute(
            "UPDATE dialogs SET totalNumberOfMessages = ? WHERE dialogId = ?",
            [self.totalMessages, self.id],
        )

        self.progress: prog = prog(self.totalMessages)

        self.file: file = file(self.config.fileSizeThresholdInBytes)

        self.error: err = err(
            self.id, self.conn, self.cursor, self.progress, self.file, self
        )

        self.users = set()

        checkpoint: list = self.getCheckpoint()
        self.progress.useCheckpoint(checkpoint)

        self.conn.commit()

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
        logger.info("Started the arciving loop")
        try:
            lastRefreshOfProgress = time.monotonic()
            with Live(str(self.progress), auto_refresh=False) as live:
                async for message in self.client.iter_messages(
                    self.dialog.entity,
                    reverse=True,
                    offset_id=self.progress.lastMessageID,
                ):
                    await self.archiveMessage(message)

                    if (
                        self.progress.update(message.id)
                        or time.monotonic() - lastRefreshOfProgress > 5
                    ):
                        lastRefreshOfProgress = time.monotonic()
                        live.update(str(self.progress), refresh=True)

                live.update(str(self.progress), refresh=True)

            logger.info("Done archiving messages")

            if self.config.dialogInfo:
                logger.info("Parsing dialog info")
                await helpers.info.getDialogInfo(
                    self.client, self.dialog, self.users, self.error, self.cursor
                )

            if self.config.userInfo:
                logger.info("Parsing users info")
                await helpers.info.usersHandler(
                    self.client,
                    self.dialog,
                    self.users,
                    self.error,
                    self.cursor,
                )

            self.saveCheckpoint()

            self.conn.commit()
            self.conn.close()
            logger.info(
                f"Done archiving {self.dialog.name} after {time.perf_counter() - self.progress.timeStart} seconds"
            )

        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            logger.info(f"Exiting mid-archiving the dialog {self.dialog.name}")
            self.handleKeyInterruption()

        except Exception as e:
            logger.exception(f"Exception occurred : {e}")
            await self.error.handle(e)

    def saveCheckpoint(self) -> None:
        logger.info("Saving the checkpoint")
        dialog = self.getCheckpoint()
        args = [
            self.progress.lastMessageID,
            self.progress.messageCounter,
            self.progress.timeStart,
        ]
        for i, value in enumerate(args[:-1]):
            if value:
                dialog[i] = value

        if self.progress.timeStart:
            dialog[-1] = time.perf_counter() - self.progress.timeStart

        dialog.append(self.dialog.id)

        self.cursor.execute(
            """
            UPDATE dialogs 
            SET 
                lastMessageId = ?,
                messageCounter = ?, 
                archivingTime = ?
            WHERE dialogId = ?
        """,
            dialog,
        )

    def getCheckpoint(self) -> list:
        self.cursor.execute(
            "SELECT * FROM dialogs WHERE dialogId = ?", [self.dialog.id]
        )

        return list(self.cursor.fetchone()[-3:])

    async def archiveMessage(self, message: custom.message.Message):
        # for writing into the file at once
        dialogId = self.id
        messageId = message.id
        authorName = ""
        views = message.views
        senderId = 0
        forwardFromName = ""
        forwardFromId = 0
        replyedToId = 0
        text = ""
        date = message.date
        editDate = message.edit_date
        filePath = ""
        fileId = 0
        fileSize = 0.0
        bigFileFlag = 0

        if self.config.texts:
            [authorName, senderId] = helpers.info.userIdHandler(message, self.users)
            [forwardFromName, forwardFromId] = helpers.text.forwardHandler(
                message, self.users
            )
            replyedToId = helpers.text.replyHandler(message, self.users)
            text = helpers.text.textHandler(message)

        if self.config.files and message.file:
            [filePath, fileId, fileSize, bigFileFlag] = await self.file.handle(message)
            self.progress.sizeInMb += message.file.size / self.progress.MbToByte

        if self.config.reactions:
            await helpers.reactions.reactionHandler(
                self.client, self.dialog, message, self.cursor
            )

        self.cursor.execute(
            """
            INSERT OR IGNORE INTO messages 
            (dialogId, messageId, authorName, views, senderId, forwardFromUsername, 
            forwardFromUserId, replyedToId, text, date, editDate,
            filePath, fileId, fileSize, downloadedMedia) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                dialogId,
                messageId,
                authorName,
                views,
                senderId,
                forwardFromName,
                forwardFromId,
                replyedToId,
                text,
                date,
                editDate,
                filePath,
                fileId,
                fileSize,
                bigFileFlag,
            ],
        )

    def handleKeyInterruption(self):
        print("\nPlease wait a moment while the saving the checkpoint")
        logger.info("Handling key interruption")

        self.saveCheckpoint()

        if self.config.userInfo:
            for user in self.users:
                helpers.info.insertUsersIntoDB(self.cursor, user, self.dialog.id)

        self.conn.commit()
        self.conn.close()

        # helpers.utils.clearLastLine()
        logger.info("Done handling key interruption")
        return
