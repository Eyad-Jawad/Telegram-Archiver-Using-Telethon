import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, custom, errors, functions, types

from db.models import StickerSet

logger = logging.getLogger(__name__)


@dataclass
class StickerSetInfo:
    id: int
    link: str
    title: str
    access_hash: int


async def find_sticker_set_in_db(
    session: AsyncSession, id: int, hash: int
) -> StickerSetInfo | None:
    """
    A function that gets info about the sticker set from the database, in case it was
    archived before so we can skip sending another api call.
    """

    stmt = select(
        StickerSet.pack_name,
        StickerSet.pack_link,
        StickerSet.sticker_set_id,
        StickerSet.access_hash,
    ).where(StickerSet.sticker_set_id == id, StickerSet.access_hash == hash)

    result = await session.execute(stmt)

    query = result.first()

    if query is None:
        return None

    return StickerSetInfo(
        title=query[0],
        link=query[1],
        id=query[2],
        access_hash=query[3],
    )


async def get_sticker_set_info(
    client: TelegramClient, message_sticker_set: types.InputStickerSetID
) -> StickerSetInfo:
    """
    A function that sends an api request to telegram to get info about the sticker set.
    """
    try:
        sticker_set = await client(
            functions.messages.GetStickerSetRequest(
                stickerset=message_sticker_set, hash=0
            )
        )

        sticker_set = sticker_set.set

        return StickerSetInfo(
            id=message_sticker_set.id,
            link="https://t.me/addstickers/" + sticker_set.short_name,
            title=sticker_set.title,
            access_hash=message_sticker_set.access_hash,
        )
    except (
        errors.EmoticonStickerpackMissingError,
        errors.rpcerrorlist.StickersetInvalidError,
    ):
        # means the sticker set does not exist
        return StickerSetInfo(
            id=message_sticker_set.id,
            link="Pack is unavailable",
            title="",
            access_hash=message_sticker_set.access_hash,
        )
    except Exception:
        logger.exception("An exception occurred.")
        return StickerSetInfo(
            id=message_sticker_set.id,
            link="",
            title="",
            access_hash=message_sticker_set.access_hash,
        )


def insert_sticker_set_info(
    session: AsyncSession,
    dialog_id: int,
    message_id: int,
    sticker_set_info: StickerSetInfo,
) -> None:
    """
    A function that takes a set of info about a sticker set and
    inserts it into the database.
    """

    # Just for safety
    if not sticker_set_info:
        return

    new_sticker_set = StickerSet(
        dialog_id=dialog_id,
        message_id=message_id,
        pack_name=sticker_set_info.title,
        pack_link=sticker_set_info.link,
        sticker_set_id=sticker_set_info.id,
        access_hash=sticker_set_info.access_hash,
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
    """

    # Just for safety
    if not message or not message.file or not message.file.sticker_set:
        return

    sticker_set = message.file.sticker_set

    if isinstance(sticker_set, types.InputStickerSetEmpty):
        return

    # Check if the sticker set was archived before so we can
    # skip an api call
    result = await find_sticker_set_in_db(
        session, sticker_set.id, sticker_set.access_hash
    )

    if result is None:
        result = await get_sticker_set_info(client, sticker_set)

    insert_sticker_set_info(session, dialog_id, message.id, result)
