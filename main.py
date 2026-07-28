import os
import asyncio
import signal
import logging

from dotenv import load_dotenv
from telethon import TelegramClient, types
from datetime import datetime
from helpers.local_utils import parse_args, clear_last_line
from objects.config import Config
from objects.dialog import Dialog

"""

TODO:
Unit tests / pytest
Handle migration
Sticker packs handler
forwarded from Pic
stories
special emoticon
reverse the process (GUI)

"""

logger = logging.getLogger(__name__)


async def main():
    # Set up the main tasks so we can cancel them if interruptted mid-archiving
    loop = asyncio.get_running_loop()
    mainTask = asyncio.current_task()
    logging.basicConfig(filename="archiving.log", level=logging.INFO)

    def handle_key_interruption():
        """Safely exists the program in case of key interruption mid an async code"""
        mainTask.cancel()
        logger.info("Exited the program.")

    # Parse the config provided from user in CLI
    config: Config = Config()
    parse_args(config)

    logger.info(f"Started at {datetime.now()} with config: {config}")

    # This is th directory where we'll save files/images or any of the sort
    os.makedirs("Media/", exist_ok=True)

    try:
        # Loop through the dialogs of the user.
        # Anohter way to do this is to call get_dialogs and loop through them instead.
        async for dialog in client.iter_dialogs():
            try:
                ans = input(f"Do you want to archive {dialog.name}? (y) ")
                clear_last_line()
            except KeyboardInterrupt:
                logger.info("Exited the program.")
                exit(0)

            if ans.lower() != "y": continue

            # Set up the dialog object
            dialog_obj = Dialog(client, config, dialog)
            logger.info(f"Archiving {dialog.name}...")

            # Again, this is for key interruption
            try:
                loop.add_signal_handler(signal.SIGINT, handle_key_interruption)
            except NotImplementedError:
                pass

            try:
                # Set up the dialog object (async part)
                # (Since you can't run async code in __init__)
                await dialog_obj.set_up()

                # This check is for safety, in the future I might add 
                # a way to give the entity id an input, and the user 
                # might input an entity not supported by the code
                if isinstance(
                    dialog.entity, (types.Chat, types.Channel, types.User)
                ):
                    # Do the archiving, this method handles everything
                    await dialog_obj.archive()
                else:
                    logger.error(
                        f"Error, cannot archive this dialog, unknown dialog type: {dialog.entity}"
                    )
            finally:
                try:
                    loop.remove_signal_handler(signal.SIGINT)
                except NotImplementedError:
                    pass

    # These errors are for key interruption
    except asyncio.CancelledError:
        # Key interruption mid async code
        print("\nPlease wait a moment while the saving the checkpoint")
        logger.info("Exited mid-archiving the dialog...")

    except KeyboardInterrupt:
        # Key interruption mid sync code
        logger.info("Exited the program.")
        print("\n\nHave a good day!")
        exit(0)


if __name__ == "__main__":
    # Get the API keys
    load_dotenv()

    API_ID = os.getenv("TELEGRAM_API_KEY")
    API_HASH = os.getenv("TELEGRAM_API_HASH")

    client = TelegramClient("Scrapper", API_ID, API_HASH)

    with client:
        try:
            client.loop.run_until_complete(main())

        except asyncio.CancelledError:
            pass
