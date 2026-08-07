import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, custom, errors, functions, types

from db.models import StickerSet

logger = logging.getLogger(__name__)


async def find_sticker_set_in_db(
    session: AsyncSession, id: int, hash: int
) -> tuple[str, str, int, int] | None:
    """
    A function that gets info about the sticker set from the database, in case it was
    archived before so we can skip sending another api call.

    Args:
        session (sqlalchemy.ext.asyncio.AsyncSession):
            The async session of the database.

        id (int):
            The id of the sticker set.

        hash (int):
            The access hash to the sticker set.

    Returns:
        tuple[
            str (The title of the sticker set),
            str (The link to the sticker set),
            int (The id of the sticker set),
            int (The access hash to the sticker set),
        ]
    """

    stmt = select(
        StickerSet.pack_name,
        StickerSet.pack_link,
        StickerSet.sticker_set_id,
        StickerSet.access_hash,
    ).where(StickerSet.sticker_set_id == id, StickerSet.access_hash == hash)

    result = await session.execute(stmt)

    query = result.one_or_none()

    if query is None:
        return None

    return (
        query[0],
        query[1],
        query[2],
        query[3],
    )


async def get_sticker_set_info(
    client: TelegramClient, message_sticker_set: types.InputStickerSetID
) -> tuple[str, str, int, int]:
    """
    A function that sends an api request to telegram to get info about the sticker set.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        message_sticker_set (telethon.types.InputStickerSetID):
            The sticker set that we want info about, accessed
            from message.file.sticker_set.

    Returns:
        tuple[
            str (The title of the sticker set),
            str (The link to the sticker set),
            int (The id of the sticker set),
            int (The access hash to the sticker set),
        ]
    """
    try:
        sticker_set = await client(
            functions.messages.GetStickerSetRequest(
                stickerset=message_sticker_set, hash=0
            )
        )

        sticker_set = sticker_set.set

        return (
            sticker_set.title,
            "https://t.me/addstickers/" + sticker_set.short_name,
            message_sticker_set.id,
            message_sticker_set.access_hash,
        )
    except (
        errors.EmoticonStickerpackMissingError,
        errors.rpcerrorlist.StickersetInvalidError,
    ):
        # means the sticker set does not exist
        return (
            "",
            "Pack is unavailable",
            message_sticker_set.id,
            message_sticker_set.access_hash,
        )
    except Exception:
        logger.exception("An exception occurred.")
        return ("", "", message_sticker_set.id, message_sticker_set.access_hash)


def insert_sticker_set_info(
    session: AsyncSession,
    sticker_set_info: tuple[int, int, str, str, int, int],
) -> None:
    """
    A function that takes a set of info about a sticker set and
    inserts it into the database.

    Args:
        session (sqlalchemy.ext.asyncio.AsyncSession):
            The async session of the database.

        sticker_set_info (tuple[
            int (Dialog id),
            int (Message id),
            str (The title of the sticker set),
            str (The link to the sticker set),
            int (The id of the sticker set),
            int (The access hash to the sticker set),
        ])

    """

    # Just for safety
    if not sticker_set_info:
        return

    new_sticker_set = StickerSet(
        dialog_id=sticker_set_info[0],
        message_id=sticker_set_info[1],
        pack_name=sticker_set_info[2],
        pack_link=sticker_set_info[3],
        sticker_set_id=sticker_set_info[4],
        access_hash=sticker_set_info[5],
    )

    session.add(new_sticker_set)


async def stickers_handler(
    client: TelegramClient,
    message: custom.Message,
    dialog_id: int,
    session: AsyncSession,
) -> None:
    """
    A function that handles things having to do with stickers, it archives the
    title and link to a sticker set, as well as the necessary info to retreive
    the sticker set again in case it changes title or link.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        dialog_id (int):
            The id of the entity where the message is.

        session (sqlalchemy.ext.asyncio.AsyncSession):
            The async session of the database.
    """

    # Just for safety
    if not message or not message.file or not message.file.sticker_set:
        return

    sticker_set = message.file.sticker_set

    if isinstance(sticker_set, types.InputStickerSetEmpty):
        return

    message_info = (dialog_id, message.id)

    # Check if the sticker set was archived before so we can
    # skip an api call
    result = await find_sticker_set_in_db(
        session, sticker_set.id, sticker_set.access_hash
    )
    if result:
        insert_sticker_set_info(session, message_info + result)
        return

    result = await get_sticker_set_info(client, sticker_set)
    if not result:
        return

    insert_sticker_set_info(session, message_info + result)
