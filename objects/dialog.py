import asyncio
import sqlite3
import time
import logging
from telethon import TelegramClient, types, utils, custom
from rich.console import Console

from helpers.info import (
    user_id_handler,
    entity_handler,
    get_dialog_info,
    insert_users_ids,
)
from helpers.text import *
from helpers.reactions import reaction_handler
from helpers.tables import make_tables
from .errors import Errors as err
from .file import File as file
from .config import Config as con
from .progress import Progress as prog

logger = logging.getLogger(__name__)


class Dialog:
    def __init__(self, client: TelegramClient, config: con, dialog) -> None:
        """
        Initialize the sync part of the class.

        Args:
            client (telethon.TelegramClient):
                Your account's client.

            config (objects.config.Config):
                The config object which is parsed from user in CLI.

            dialog (telethon.tl.custom.dialog.Dialog):
                The object which you get from client.iter_dialogs.
        """

        logger.info("Initiating the dialog class (the synchronous part)...")

        # Telethon objects
        self.client = client
        self.dialog = dialog
        self.entity = dialog.entity

        # Useful metadata parsed from telethon objects
        self.id: int = utils.get_peer_id(dialog.entity)
        self.type: str = self.get_dialog_type()

        self.config: con = config

        # The database connection
        self.conn = sqlite3.connect("telegram.db")
        self.cursor = self.conn.cursor()

        # Initialize the database by creating all the tables and inserting the dialog
        make_tables(self.cursor)
        self.cursor.execute(
            "INSERT OR IGNORE INTO dialogs (dialog_id, name, type) VALUES  (?, ?, ?)",
            [self.id, self.dialog.name, self.type],
        )

        self.conn.commit()

    async def set_up(self) -> None:
        """Initialize the async part of the class."""

        logger.info("Initiating the dialog class (the asynchronous part)...")

        # Get the total number of actual messeages in the dialog.
        self.total_messages: int = (
            await self.client.get_messages(self.dialog, limit=0)
        ).total

        self.cursor.execute(
            "UPDATE dialogs SET total_number_of_messages = ? WHERE dialog_id = ?",
            [self.total_messages, self.id],
        )

        # Initialize the needed objects
        self.progress: prog = prog(self.total_messages, self.dialog.name)

        self.file: file = file(self.config.size_threshold)

        self.error: err = err(self.conn, self.progress, self)

        self.users = set()  # A set that collects entities over archiving time.

        # Get the progress in case this dialog was archived before.
        checkpoint: tuple = self.get_checkpoint()
        self.progress.use_checkpoint(checkpoint)

        self.conn.commit()

    def get_dialog_type(self) -> str:
        """A method that returns the type of the dialog as a string."""
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
        """The main archiving loop for the dialog."""

        logger.info("Started the archiving loop...")

        try:
            last_progress_refresh = time.monotonic() - 10
            progress_console = Console()
            with progress_console.screen() as screen:
                # The progress panel in the CLI.
                async for message in self.client.iter_messages(
                    self.dialog.entity,
                    reverse=True,  # Start from the oldest message.
                    offset_id=self.progress.last_message_id,  # Skip already archived messages.
                ):
                    # Archive the message, this method handles it all
                    await self.archive_message(message)

                    # If 5 seconds have passed, or multipls of 10% messages were archived,
                    # update the progress panel in the CLI.
                    if time.monotonic() - last_progress_refresh > 5:
                        last_progress_refresh = time.monotonic()
                        screen.update(self.progress.make_table(), self.progress.bar)

                # Ensure the progress panel is showed at 100% at the end.
                screen.update(self.progress.make_table(), self.progress.bar)

            logger.info("Done archiving messages.")

            # Check if the user wants to archive dialog's metadata
            if self.config.dialog_metadata:
                logger.info("Parsing dialog metadata...")
                await get_dialog_info(
                    self.client, self.dialog, self.users, self.error, self.cursor
                )

            # Check if the user wants to archive users' metadata
            if self.config.user_metadata:
                logger.info("Parsing users metadata...")
                await entity_handler(
                    self.client,
                    self.dialog,
                    self.users,
                    self.error,
                    self.cursor,
                )

            self.save_checkpoint()

            self.conn.commit()
            self.conn.close()
            logger.info(
                f"Done archiving {self.dialog.name} after {time.perf_counter() - self.progress.time_start} seconds."
            )

        # Handle key interruption
        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            logger.info(f"Exiting mid-archiving the dialog {self.dialog.name}...")
            self.handle_key_interruption()

        # Handle other unknown errors
        except Exception as e:
            logger.exception(f"Exception occurred : {e}")
            await self.error.handle(e)

    def save_checkpoint(self) -> None:
        """A method that saves the progress of archiving in the database for future archiving."""

        logger.info("Saving the checkpoint...")

        # Get the past checkpoint in case some data was not initialized
        checkpoint = list(self.get_checkpoint())
        args = [
            self.progress.last_message_id,
            self.progress.message_counter,
            time.perf_counter() - self.progress.time_start,
        ]
        # If however the data was initialized, then assign it
        for i, value in enumerate(args):
            if value:
                checkpoint[i] = value

        checkpoint.append(self.dialog.id)

        self.cursor.execute(
            """
            UPDATE dialogs 
            SET 
                last_message_id = ?,
                message_counter = ?, 
                archiving_time = ?
            WHERE dialog_id = ?
        """,
            checkpoint,
        )

    def get_checkpoint(self) -> tuple[int, int, float]:
        """
        Get the past checkpoint of progerss in archiving the dialog if it exists.

        Returns:
            Tuple: [
                last_message_id: int,
                message_counter: int,
                archiving_time: float,
            ]
        """

        self.cursor.execute(
            """
            SELECT last_message_id, message_counter, archiving_time
            FROM dialogs
            WHERE dialog_id = ?
        """,
            [self.dialog.id],
        )

        return self.cursor.fetchone()

    async def archive_message(self, message: custom.message.Message) -> None:
        """
        A method for archiving, and exctracting data from a telegram message.

        Args:
            message (telethon.custom.message.Message):
                A telegram dialog's message provided by telethon.
        """

        # for writing into the file at once
        dialog_id = self.id
        message_id = message.id
        author_name = ""
        views = message.views
        sender_id = 0
        forward_from_name = ""
        forward_from_id = 0
        replied_to_id = 0
        text = ""
        date = message.date
        edit_date = message.edit_date
        file_path = ""
        file_id = ""
        file_size = 0.0
        downloaded_file = False

        # Check if the user wants to archive text data
        if self.config.texts:
            author_name, sender_id = user_id_handler(message, self.users)
            forward_from_name, forward_from_id = forward_handler(message, self.users)
            replied_to_id = reply_handler(message, self.users)
            text = text_handler(message)

        # Check if the user wants to archive files
        if self.config.files and message.file:
            file_path, file_id, file_size, downloaded_file = await self.file.handle(
                message
            )

            # If the user doesn't want to archive files, the
            # program will save the files' metadata either way
            # and self.config.files would be true, but the size
            # threshold is 0
            if self.config.size_threshold != 0:
                self.progress.update_file_progress(message.file.size)

        # Check if the user wants to archive reactions
        if self.config.reactions:
            await reaction_handler(self.client, self.dialog, message, self.cursor)

        self.cursor.execute(
            """
            INSERT OR IGNORE INTO messages 
            (dialog_id, message_id, author_name, views, sender_id, forward_from_username, 
            forward_from_user_id, replied_to_id, text, date, edit_date,
            file_path, file_id, file_size, downloaded_file) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                dialog_id,
                message_id,
                author_name,
                views,
                sender_id,
                forward_from_name,
                forward_from_id,
                replied_to_id,
                text,
                date,
                edit_date,
                file_path,
                file_id,
                file_size,
                downloaded_file,
            ],
        )
        self.progress.update(message_id)

    def handle_key_interruption(self) -> None:
        """A method for existing safely when interrupted mid archiving."""

        print("\nPlease wait a moment while the saving the checkpoint")
        logger.info("Handling key interruption...")

        # Save checkpoint, most important thing in this method
        self.save_checkpoint()

        """
        Check if the user wants to save user data.

        In this situation, a user might be saved
        when archiving a dialog, but now if we 
        resume archiving, that user's id will be lost,
        so it's good to save it in the database at least 
        as an id only.
        """
        if self.config.user_metadata:
            for user in self.users:
                insert_users_ids(self.cursor, user, self.dialog.id)

        self.conn.commit()
        self.conn.close()

        # utils.clearLastLine()
        logger.info("Done handling key interruption.")
        return
