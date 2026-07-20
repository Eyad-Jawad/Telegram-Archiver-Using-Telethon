import os, argparse, objects, helpers, asyncio, signal, logging
from dotenv import load_dotenv
from telethon import TelegramClient, types
from datetime import datetime

"""

TODO:
invert how dialogInfoArchive work
Unit tests / pytest
Handle migration
Sticker packs handler
forwarded from Pic
stories
special emoticon
reverse the process (GUI)
comments

"""

logger = logging.getLogger(__name__)


async def main():
    loop = asyncio.get_running_loop()
    mainTask = asyncio.current_task()
    logging.basicConfig(filename="archiving.log", level=logging.INFO)

    def handleKeyInterruption():
        mainTask.cancel()
        logger.info("Exited the program.")

    config = objects.config.Config()
    helpers.utils.parseArgs(config)

    logger.info(f"Started at {datetime.now()} with config: {config}")
    os.makedirs("Media/", exist_ok=True)

    try:
        async for dialog in client.iter_dialogs():
            try:
                ans = input(f"Do you want to archive {dialog.name}? (y) ")
                helpers.utils.clearLastLine()
            except KeyboardInterrupt:
                logger.info("Exited the program.")
                exit(0)

            if ans == "y":
                dialogClass = objects.dialog.Dialog(client, config, dialog)
                logger.info(f"Archiving {dialog.name}...")

                try:
                    loop.add_signal_handler(signal.SIGINT, handleKeyInterruption)
                except NotImplementedError:
                    pass

                try:
                    await dialogClass.setUp()

                    if isinstance(
                        dialog.entity, (types.Chat, types.Channel, types.User)
                    ):
                        await dialogClass.archive()
                    else:
                        logger.error(
                            "Error, cannot archive this dialog, unknown dialog type"
                        )
                finally:
                    try:
                        loop.remove_signal_handler(signal.SIGINT)
                    except NotImplementedError:
                        pass

    except asyncio.CancelledError:
        print("\nPlease wait a moment while the saving the checkpoint")
        logger.info("Exited mid-archiving the dialog...")
    except KeyboardInterrupt:
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
