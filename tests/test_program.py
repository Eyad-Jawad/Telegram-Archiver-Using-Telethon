import os, objects, pytest, shutil, hashlib
from dotenv import load_dotenv
from telethon import TelegramClient
from pathlib import Path

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_KEY")
API_HASH = os.getenv("TELEGRAM_API_HASH")

client = TelegramClient("Scrapper", API_ID, API_HASH)


async def setUp():
    config = objects.config.Config()
    config.texts = True
    config.reactions = True
    config.dialogInfo = True
    config.userInfo = True
    config.files = True
    config.fileSizeThresholdInBytes = float("inf")

    path = "dialogs/Supergroup/-1003761332472"
    if os.path.isdir(path):
        shutil.rmtree(path)

    os.makedirs(path)

    async for dialog in client.iter_dialogs():
        if dialog.id != -1003761332472:
            continue

        dialogClass = objects.dialog.Dialog(client, config, dialog)
        await dialogClass.setUp()
        await dialogClass.archive()
        break


def getHash():
    sha256 = hashlib.sha256()

    path = "dialogs/Supergroup/-1003761332472/"
    files = [
        list(Path(path + "Dialog Info/").rglob("*.jpg"))[0],
        path + "Dialog Info/PhotoInfo.csv",
        path + "files/2 .jpg",
        path + "files/3 sticker.webp",
        path + "files/bigfiles.csv",
        path + "Reactions.csv",
        path + "TextMessages.csv",
    ]
    # we ignore info, CheckPoint, errors, and Users because they can change

    CHUNK_SIZE = 8192  # 8kb
    for file in files:
        with open(file, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)

                if not chunk:
                    break

                sha256.update(chunk)

    return sha256.hexdigest()


@pytest.mark.asyncio
async def test():
    await client.connect()
    try:
        await setUp()
        assert (
            getHash()
            == "a274344c51c0a727babecdf3a02a5b9e103b54b57f3290a27725f0acff12efcc"
        )
    finally:
        await client.disconnect()
