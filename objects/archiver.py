import asyncio
import logging
import time

from rich.console import Console
from sqlalchemy import select
from telethon import TelegramClient, custom, types, utils

from db import get_session
from db.models import Dialog, Message
from helpers.info import (
    entity_handler,
    get_dialog_info,
    insert_users_ids,
    user_id_handler,
)
from helpers.reactions import reaction_handler
from helpers.stickers import stickers_handler
from helpers.text import *

from .config import Config as con
from .file_handler import make_file_handler
from .progress import Progress as prog
from .progress import ProgressFileDelegation

logger = logging.getLogger(__name__)
BATCH_SIZE = 700


class Archiver:
    def __init__(self, client: TelegramClient, config: con, dialog) -> None:
        """
        Initialize the sync part of the class. Must call `await Archiver.set_up()` afterwards.
        """

        logger.debug("Initiating the dialog class (the synchronous part)...")

        # Telethon objects
        self.client = client
        self.dialog = dialog
        self.entity = dialog.entity

        # Useful metadata parsed from telethon objects
        self.id: int = utils.get_peer_id(dialog.entity)
        self.type: str = self.get_dialog_type()

        self.config: con = config

        # The database session
        self.session = get_session()

        # Initialize the database by creating all the tables and inserting the dialog
        self.db_dialog = Dialog(
            dialog_id=self.id, name=self.dialog.name, type=self.type
        )
        self.session.add(self.db_dialog)

    async def set_up(self) -> None:
        """Initialize the async part of the class."""
        await self.session.commit()

        logger.debug("Initiating the dialog class (the asynchronous part)...")

        # Get the total number of actual messeages in the dialog.
        self.total_messages: int = (
            await self.client.get_messages(self.dialog, limit=0)
        ).total

        stmt = select(Dialog).where(Dialog.dialog_id == self.id)
        result = await self.session.execute(stmt)
        self.db_dialog = result.scalar_one()
        self.db_dialog.total_number_of_messages = self.total_messages

        await self.session.commit()

        # Initialize the needed objects
        self.progress: prog = prog(self.total_messages, self.dialog.name)

        self.file_handler = make_file_handler(
            self.config.size_threshold, ProgressFileDelegation(self.progress)
        )

        self.users: set[int] = (
            set()
        )  # A set that collects entities over archiving time.

        # Get the progress in case this dialog was archived before.
        checkpoint: tuple = await self.get_checkpoint()
        self.progress.use_checkpoint(checkpoint)

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

        logger.debug("Started the archiving loop...")

        last_progress_refresh = time.monotonic() - 10
        progress_console = Console()
        current_msg_count = 0

        try:
            with progress_console.screen() as screen:
                # The progress panel in the CLI.
                async for message in self.client.iter_messages(
                    self.entity,
                    reverse=True,  # Start from the oldest message.
                    offset_id=self.progress.last_message_id,  # Skip already archived messages.
                ):
                    # If 5 seconds have passed, update the progress panel in the CLI.
                    if time.monotonic() - last_progress_refresh > 5:
                        last_progress_refresh = time.monotonic()
                        screen.update(
                            self.progress.make_table(), self.progress.bar
                        )

                    # Archive the message, this method handles it all
                    await self.archive_message(message)

                    current_msg_count += 1
                    if current_msg_count % BATCH_SIZE == 0:
                        await self.save_checkpoint()

            # Ensure the progress panel is showed at 100% at the end.
            progress_console.print(
                self.progress.make_table(), self.progress.bar
            )

            logger.info("Done archiving messages.")

            # Check if the user wants to archive dialog's metadata
            if self.config.dialog_metadata:
                progress_console.print("Parsing dialog's metadata...")
                await get_dialog_info(
                    self.client,
                    self.dialog,
                    self.users,
                    self.session,
                )

            # Check if the user wants to archive users' metadata
            if self.config.user_metadata:
                progress_console.print("Parsing users' metadata...")
                await entity_handler(
                    self.client,
                    self.dialog,
                    self.users,
                    self.session,
                )

            await self.save_checkpoint()

            await self.session.close()
            logger.info(
                f"Done archiving {self.dialog.name} after {time.perf_counter() - self.progress.time_start} seconds."
            )

            progress_console.clear()
            progress_console.print(f"Done archiving {self.dialog.name}!\n\n")

        # Handle key interruption
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info(
                f"Exiting mid-archiving the dialog {self.dialog.name}..."
            )
            await self.handle_key_interruption()

        # Handle other unknown errors
        except Exception:
            logger.exception(
                f"Exception occurred with dialog {self.id} : {self.dialog.name}"
            )

    async def save_checkpoint(self) -> None:
        """A method that saves the progress of archiving in the database for future archiving."""

        logger.info("Saving the checkpoint...")

        # Get the past checkpoint in case some data was not initialized
        checkpoint = list(await self.get_checkpoint())
        args = [
            self.progress.last_message_id,
            self.progress.message_counter,
            time.perf_counter() - self.progress.time_start,
        ]
        # If however the data was initialized, then assign it
        for i, value in enumerate(args):
            if value:
                checkpoint[i] = value

        self.db_dialog.last_message_id = int(checkpoint[0])  # For mypy
        self.db_dialog.message_counter = int(checkpoint[1])  # For mypy
        self.db_dialog.archiving_time = checkpoint[2]

        await self.session.commit()

    async def get_checkpoint(self) -> tuple[int, int, float]:
        """
        Get the past checkpoint of progerss in archiving the dialog if it exists.

        Returns:
            Tuple: [
                last_message_id: int,
                message_counter: int,
                archiving_time: float,
            ]
        """

        return (
            self.db_dialog.last_message_id,
            self.db_dialog.message_counter,
            self.db_dialog.archiving_time,
        )

    async def archive_message(self, tel_msg: custom.message.Message) -> None:
        """
        A method for archiving, and exctracting data from a telegram message.
        """

        db_msg = Message()
        db_msg.dialog_id = self.id
        db_msg.message_id = tel_msg.id
        db_msg.views = tel_msg.views
        db_msg.date = tel_msg.date
        db_msg.edit_date = tel_msg.edit_date

        tasks = []

        # Check if the user wants to archive text data
        if self.config.texts:
            user_id_handler(tel_msg, db_msg, self.users)
            forward_handler(tel_msg, db_msg, self.users)
            reply_handler(tel_msg, db_msg, self.users)
            text_handler(tel_msg, db_msg)

        # Check if the user wants to archive files
        if self.config.files and tel_msg.file:
            tasks.append(self.file_handler(tel_msg, db_msg))

        # Check if the user wants to archive stickers, and if
        # this message is a sticker
        if self.config.stickers:
            tasks.append(
                stickers_handler(self.client, tel_msg, self.id, self.session)
            )

        # Check if the user wants to archive reactions
        if self.config.reactions:
            tasks.append(
                reaction_handler(
                    self.client, self.dialog, tel_msg, self.session
                )
            )

        await asyncio.gather(*tasks)

        self.session.add(db_msg)

        self.progress.update(tel_msg.id)

    async def handle_key_interruption(self) -> None:
        """A method for existing safely when interrupted mid archiving."""

        print("\nPlease wait a moment while the saving the checkpoint")
        logger.info("Handling key interruption...")

        # Save checkpoint, most important thing in this method
        await self.save_checkpoint()

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
                await insert_users_ids(self.session, user, self.id)

        await self.session.commit()
        await self.session.close()

        # utils.clearLastLine()
        logger.info("Done handling key interruption.")
