import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, custom, functions, tl, types
from telethon.errors import (
    BadRequestError,
    ChannelPrivateError,
    ChatAdminRequiredError,
)

from db.models import DialogMetadata, DialogPhoto, Message, User

from .local_utils import construct_fake_dialog

logger = logging.getLogger(__name__)


@dataclass
class PhotoInfo:
    dialog_id: int
    photo_id: int
    path: str
    date: str


def user_id_handler(
    tel_msg: custom.message.Message, db_msg: Message, users: set[int]
) -> None:
    """
    A function that parses user id from messages, or post author name
    in case of channels.
    """

    try:
        # If it is a channel set the post author name and return
        if tel_msg.post_author:
            db_msg.author_name = tel_msg.post_author
            return

        # If for some reason it's not a channel and there's
        # no sender id just return
        elif not tel_msg.sender_id:
            logger.warning(
                f"A message where no name or id was received: {tel_msg}."
            )
            return

        # check if the sender is not saved
        if tel_msg.sender_id not in users:
            users.add(tel_msg.sender_id)

        db_msg.sender_id = tel_msg.sender_id
        return

    except Exception:
        logger.exception(f"Exception occurred at message {tel_msg.id}")
        return


async def get_latest_photo_date(
    session: AsyncSession, dialog_id: int
) -> datetime:
    """
    A function that gets the date of the latest profile photo
    for entities, so that you only donwload photos that are newer
    than the last one saved.
    """

    # format: 2026-03-06 17:45:25+00:00

    stmt = select(func.max(DialogPhoto.photo_date)).where(
        DialogPhoto.dialog_id == dialog_id
    )

    result = await session.execute(stmt)

    query = result.scalar()

    if not query:
        return datetime(1900, 1, 1, tzinfo=UTC)  # arbitrary date
    else:
        return query


def insert_dialog_metadata(
    session: AsyncSession, dialog_id: int, full_request: str
) -> None:
    """
    A function that inserts dialog metadata into dialog_metadata.
    """

    new_dialog_metadata = DialogMetadata(
        dialog_id=dialog_id, full_request=full_request
    )
    session.add(new_dialog_metadata)


def insert_photo_info(
    session: AsyncSession, photo_info: list[PhotoInfo]
) -> None:
    """
    A function that inserts photo data acquired from get_photo_info
    into the database.
    """

    for row in photo_info or []:
        session.add(
            DialogPhoto(
                dialog_id=row.dialog_id,
                photo_id=row.photo_id,
                photo_path=row.path,
                photo_date=row.date,
            )
        )


async def get_dialog_info(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
    session: AsyncSession,
) -> None:
    """
    A function that handles all things having to do with info, user ids, or metadata
    """

    full_request = await get_full_request(client, dialog.entity)
    insert_dialog_metadata(session, dialog.entity.id, full_request)

    latest_photo_date = await get_latest_photo_date(session, dialog.entity.id)
    photo_info = await get_photo_info(client, dialog.entity, latest_photo_date)
    insert_photo_info(session, photo_info)

    await add_users_to_set(client, dialog, users)


async def get_full_request(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
) -> str:
    """
    A function that gets the full request from telegram for
    the different types of dialogs.
    """

    try:
        full_request = None

        if isinstance(dialog, types.Channel):
            full_request = await client(
                functions.channels.GetFullChannelRequest(dialog.id)
            )

        elif isinstance(dialog, types.User):
            full_request = await client(
                functions.users.GetFullUserRequest(dialog.id)
            )

        elif isinstance(dialog, types.Chat):
            full_request = await client(
                functions.messages.GetFullChatRequest(dialog.id)
            )

        else:
            logger.warning(f"Unknown dialog type: {dialog}")
            return ""

        return full_request.stringify()
    except Exception:
        logger.exception(
            f"Exception occurred with dialog {dialog.id} : {dialog.name}"
        )
        return ""


async def get_photo_info(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    latest_photo_date: datetime,
) -> list[PhotoInfo]:
    """
    A function that downloads and gets the metadata of profile
    photos of dialogs.
    """

    # The directory where photos will be saved
    PATH = "Media/"
    photo_data = []

    try:
        async for photo in client.iter_profile_photos(dialog):
            # If it is older than the latest photo in the database skip it
            if photo.date < latest_photo_date:
                continue

            photo_path = await client.download_media(photo, file=PATH)
            photo_data.append(
                PhotoInfo(
                    dialog_id=dialog.id,
                    photo_id=photo.id,
                    path=photo_path,
                    date=photo.date,
                )
            )

    except Exception:
        logger.exception(
            f"Exception occurred with dialog {dialog.id} : {dialog.name}"
        )

    return photo_data


async def add_users_to_set(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
) -> None:
    """
    A function that parses users in chats, and adds
    them to the accumulative set of users we have.
    """

    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)

    except ChatAdminRequiredError as e:
        logger.info(
            f"You can't parse users in this chat, it's a private chat: {e}"
        )

    except ChannelPrivateError:
        logger.info(
            "You can't parse users from this channel, you are not an admin"
        )

    except BadRequestError:
        logger.warning("Something went wrong, due to that we can't parse users")

    except Exception:
        logger.exception(
            f"Exception occurred with dialog {dialog.id} : {dialog.name}"
        )


async def insert_users_ids(
    session: AsyncSession, user: int, dialog_id: int
) -> None:
    """
    A function that inserts a user's id into the database.
    """

    # For safety
    if not user or not dialog_id:
        return

    stmt = insert(User).values(user_id=user, dialog_id=dialog_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=["dialog_id", "user_id"])

    await session.execute(stmt)


async def entity_handler(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
    session: AsyncSession,
    skip_details: bool = False,
) -> None:
    """
    A function that handles the metadata of entities found in dialogs.

        skip_details (bool):
            A flag for skipping requesting metadata of users
            in a dialog in case of key interruption where we
            would only insert their ids into the database
            without any other metadata.
    """

    # For safety
    if not users:
        return

    dialog_id = dialog.entity.id

    for user in users:
        await insert_users_ids(session, user, dialog_id)

    # In case of a key interruption
    if skip_details:
        return

    # Get the metadata of users from the original dialog
    for user in users:
        entity = await client.get_entity(user)

        # Right now the function get_dialog_info uses
        # dialog.entity, and since there's not way to get
        # a dialog class, just do this trick
        fake_dialog = construct_fake_dialog(entity)

        # We pass an empty set because we don't want
        # it to function as a crawler, for now at least
        await get_dialog_info(client, fake_dialog, set(), session)
