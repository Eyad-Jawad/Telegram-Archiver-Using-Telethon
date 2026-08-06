import asyncio
import logging
import time
from db import get_session
from db.models import Dialog, Message

from rich.console import Console
from telethon import TelegramClient, custom, types, utils

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
from .errors import Errors as err
from .file import File as file
from .progress import Progress as prog

logger = logging.getLogger(__name__)


class Archiver:
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

        # The database session
        self.session = get_session()

        # Initialize the database by creating all the tables and inserting the dialog
        new_dialog = Dialog(dialog_id=self.id, name=self.dialog.name, type=self.type)
        self.session.add(new_dialog)
        self.session.flush()

    async def set_up(self) -> None:
        """Initialize the async part of the class."""

        logger.info("Initiating the dialog class (the asynchronous part)...")

        # Get the total number of actual messeages in the dialog.
        self.total_messages: int = (
            await self.client.get_messages(self.dialog, limit=0)
        ).total

        self.session.query(Dialog).filter(Dialog.dialog_id == self.id).update({"total_number_of_messages": self.total_messages})
        self.session.commit()

        # Initialize the needed objects
        self.progress: prog = prog(self.total_messages, self.dialog.name)

        self.file: file = file(self.config.size_threshold)

        self.error: err = err(self.progress, self)

        self.users: set[int] = (
            set()
        )  # A set that collects entities over archiving time.

        # Get the progress in case this dialog was archived before.
        checkpoint: tuple = self.get_checkpoint()
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

        logger.info("Started the archiving loop...")

        try:
            last_progress_refresh = time.monotonic() - 10
            progress_console = Console()
            with progress_console.screen() as screen:
                # The progress panel in the CLI.
                async for message in self.client.iter_messages(
                    self.entity,
                    reverse=True,  # Start from the oldest message.
                    offset_id=self.progress.last_message_id,  # Skip already archived messages.
                ):
                    # If 5 seconds have passed, or multipls of 10% messages were archived,
                    # update the progress panel in the CLI.
                    if time.monotonic() - last_progress_refresh > 5:
                        last_progress_refresh = time.monotonic()
                        screen.update(
                            self.progress.make_table(), self.progress.bar
                        )

                    # Archive the message, this method handles it all
                    await self.archive_message(message)

            # Ensure the progress panel is showed at 100% at the end.
            progress_console.print(
                self.progress.make_table(), self.progress.bar
            )
            progress_console.print("\n")

            logger.info("Done archiving messages.")

            # Check if the user wants to archive dialog's metadata
            if self.config.dialog_metadata:
                logger.info("Parsing dialog's metadata...")
                progress_console.print("Parsing dialog's metadata...")
                await get_dialog_info(
                    self.client,
                    self.dialog,
                    self.users,
                    self.error,
                    self.session,
                )

            # Check if the user wants to archive users' metadata
            if self.config.user_metadata:
                logger.info("Parsing users' metadata...")
                progress_console.print("Parsing users' metadata...")
                await entity_handler(
                    self.client,
                    self.dialog,
                    self.users,
                    self.error,
                    self.session,
                )

            self.save_checkpoint()

            self.session.commit()
            self.session.close()
            logger.info(
                f"Done archiving {self.dialog.name} after {time.perf_counter() - self.progress.time_start} seconds."
            )

            progress_console.clear()
            print(f"Done archiving {self.dialog.name}!\n\n")

        # Handle key interruption
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info(
                f"Exiting mid-archiving the dialog {self.dialog.name}..."
            )
            self.handle_key_interruption()

        # Handle other unknown errors
        except Exception as e:
            logger.exception(
                f"Exception occurred with dialog {self.id} : {self.dialog.name}"
            )
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

        self.session.query(Dialog).filter(Dialog.dialog_id == self.id).update(
            {
                "last_message_id": checkpoint[0],
                "message_counter": checkpoint[1],
                "archiving_time": checkpoint[2],
            }
        )

        self.session.commit()

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

        checkpoint = self.session.query(Dialog.last_message_id, Dialog.message_counter, Dialog.archiving_time).filter(Dialog.dialog_id == self.id).one()

        return checkpoint._t

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
        replied_to_entity_id = 0
        replied_to_text = ""
        text = ""
        date = message.date
        edit_date = message.edit_date
        file_path = ""
        file_name = ""
        file_id = ""
        file_size = 0.0
        downloaded_file = False

        # Check if the user wants to archive text data
        if self.config.texts:
            author_name, sender_id = user_id_handler(message, self.users)
            forward_from_name, forward_from_id = forward_handler(
                message, self.users
            )
            replied_to_id, replied_to_entity_id, replied_to_text = (
                reply_handler(message, self.users)
            )
            text = text_handler(message)

        # Check if the user wants to archive files
        if message.file:
            if self.config.files:
                file_path, file_name, file_id, file_size, downloaded_file = (
                    await self.file.handle(message)
                )

                # If the user doesn't want to archive files, the
                # program will save the files' metadata either way
                # and self.config.files would be true, but the size
                # threshold is 0
                if self.config.size_threshold != 0:
                    self.progress.update_file_progress(message.file.size)

            # Check if the user wants to archive stickers, and if
            # this message is a sticker
            if self.config.stickers and message.file.sticker_set:
                await stickers_handler(
                    self.client, message, self.id, self.session
                )

        # Check if the user wants to archive reactions
        if self.config.reactions:
            await reaction_handler(
                self.client, self.dialog, message, self.session
            )

        new_message = Message(
            dialog_id=dialog_id,
            message_id=message_id,
            author_name=author_name,
            views=views,
            sender_id=sender_id,
            forward_from_username=forward_from_name,
            forward_from_user_id=forward_from_id,
            replied_to_id=replied_to_id,
            replied_to_entity_id=replied_to_entity_id,
            replied_to_text=replied_to_text,
            text=text,
            date=date,
            edit_date=edit_date,
            file_path=file_path,
            file_name=file_name,
            file_id=file_id,
            file_size=file_size,
            downloaded_file=downloaded_file,
        )

        self.session.add(new_message)

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
                insert_users_ids(self.session, user, self.id)

        self.session.commit()
        self.session.close()

        # utils.clearLastLine()
        logger.info("Done handling key interruption.")
