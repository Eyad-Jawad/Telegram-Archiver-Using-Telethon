import os, argparse, objects, helpers
from dotenv import load_dotenv
from telethon import TelegramClient, types

"""
FIXME:
When replying to a message from a private chat the method fails:'TotalList' object has no attribute 'id'
checkpoint takes messageId instead of messageCounter

TODO:

:::::::::::::::::::::::::::::
        conn.close()
:::::::::::::::::::::::::::::

for logging, make info.insertUsers log nulls or something

Logging
Unit tests / pytest
Make it installable in pip or something idk
Handle migration
Sticker packs handler
forwarded from Pic
stories
special emoticon
edit date
reverse the process (GUI)
add the method of only extracting one's messages
On channel get views

"""


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--archive-all", action="store_true", help="archive everything"
    )
    parser.add_argument(
        "-t",
        "--archive-text",
        action="store_true",
        help="archive text messages (including forward, reply, edit, and sender_id)",
    )
    parser.add_argument(
        "-r",
        "--archive-reactions",
        action="store_true",
        help="archive message reactions",
    )
    parser.add_argument(
        "-d",
        "--archive-dialog-info",
        action="store_true",
        help="archive dialog info like title, bio, pfps, and etc.",
    )
    parser.add_argument(
        "-u",
        "--archive-user-info",
        action="store_true",
        help="archive info of users in a dialog, like name, bio, pfps, and etc.",
    )
    parser.add_argument(
        "-f",
        "--archive-file",
        action="store_true",
        help="archive files, like photos, videos, documents, and etc. with a size threshold (default: 100MB)",
    )
    parser.add_argument(
        "-b",
        "--archive-big-files",
        action="store_true",
        help="archive all files ignoring the default of 100MB",
    )
    parser.add_argument(
        "-s",
        "--size-threshold",
        default=100,
        type=int,
        metavar="MB",
        help="the size threshold for files (default: 100MB)",
    )

    config = objects.config.Config()

    args = parser.parse_args()

    if args.archive_all:
        config.texts = True
        config.reactions = True
        config.dialogInfo = True
        config.userInfo = True
        config.files = True
        config.fileSizeThresholdInBytes = float("inf")
    else:
        config.texts = args.archive_text
        config.reactions = args.archive_reactions
        config.dialogInfo = args.archive_dialog_info
        config.userInfo = args.archive_user_info
        config.files = args.archive_file

        if args.archive_big_files:
            config.files = True
            config.fileSizeThresholdInBytes = float("inf")

        elif args.archive_file:
            config.files = True
            config.fileSizeThresholdInBytes = args.size_threshold * (1024**2)

        elif args.archive_text:
            # Save only file metadata, don't download files.
            config.files = True
            config.fileSizeThresholdInBytes = 0

        else:
            config.files = False
            config.fileSizeThresholdInBytes = args.size_threshold * (1024**2)

    print("Started...")
    os.makedirs("Media/", exist_ok=True)

    async for dialog in client.iter_dialogs():
        try:
            ans = input(f"Do you want to archive {dialog.name}? (y) ")
            helpers.utils.clearLastLine()
        except KeyboardInterrupt:
            print("\n\nHave a good day!")
            exit(0)

        if ans == "y":
            dialogClass = objects.dialog.Dialog(client, config, dialog)
            await dialogClass.setUp()

            if isinstance(dialog.entity, (types.Chat, types.Channel, types.User)):
                print(f"Archiving {dialog.name}...\n\n")
                await dialogClass.archive()

            else:
                print("Error: can't archive this!")


if __name__ == "__main__":
    # Get the API keys
    load_dotenv()

    API_ID = os.getenv("TELEGRAM_API_KEY")
    API_HASH = os.getenv("TELEGRAM_API_HASH")

    client = TelegramClient("Scrapper", API_ID, API_HASH)

    with client:
        client.loop.run_until_complete(main())
