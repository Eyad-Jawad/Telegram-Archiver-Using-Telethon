import sqlite3
import logging
from types import SimpleNamespace
from telethon import TelegramClient, functions, types, custom, tl
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError, BadRequestError
from objects.errors import Errors
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def user_id_handler(
    message: custom.message.Message, users: set[int]
) -> tuple[str, int]:
    """
    A function that parses user id from messages, or post author name
    in case of channels.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

    Returns:
        tuple (
            str (Post author name in case of channels),
            int (user id)
        )
    """

    try:
        # If it is a channel return post author name
        if message.post_author:
            return (message.post_author, 0)

        # If for some reason it's not a channel and there's
        # no sender id return empty things
        elif not message.sender_id:
            logger.warning(f"A message where no name or id was recieved: {message}.")
            return ("", 0)

        # check if the sender is not saved
        if message.sender_id not in users:
            users.add(message.sender_id)

        return ("", message.sender_id)

    except Exception as e:
        logging.exception(f"Exception occurred : {e}")
        return ("", 0)


def get_latest_photo_date(cursor: sqlite3.Cursor, dialog_id: int) -> datetime:
    """
    A function that gets the date of the latest profile photo
    for entities, so that you only donwload photos that are newer
    than the last one saved.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        dialog_id (int):
            The id of the entity.

    Returns:
        Datetime:
            The latest date of a pfp if it exists, else 1900 as a default.
    """

    # format: 2026-03-06 17:45:25+00:00

    cursor.execute(
        "SELECT MAX(photo_date) FROM dialog_photos WHERE dialog_id = ?", [dialog_id]
    )

    query = cursor.fetchone()
    if not query or not query[0]:
        return datetime(1900, 1, 1, tzinfo=timezone.utc)  # arbitrary date
    else:
        return datetime.fromisoformat(query[0])


def is_archived(cursor: sqlite3.Cursor, dialog_id: int) -> bool:
    """
    A function that checks if dialog metadata was archived before.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        dialog_id (int):
            The id of the entity.

    Returns:
        bool:
            A boolean for if dialog metadata was archived before.
    """
    cursor.execute(
        "SELECT full_request FROM dialog_metadata WHERE dialog_id = ?", [dialog_id]
    )

    query = cursor.fetchone()

    return bool(query and query[0])


def insert_info_into_appropriate_table(
    cursor: sqlite3.Cursor, dialog_id: int, full_request: str
) -> None:
    """
    A function that inserts dialog metadata into dialog_metadata
    if it is the first time archiving this dialog's metadata
    or updating dialog_metadata_archive if it is not the first time
    while also inserting new metadata into dialog_metadata.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        dialog_id (int):
            The id of the entity.

        full_request (str):
            A srting of the full request recieved from telegram of
            the dilaog we are archiving its metadata.
    """

    # Check if the dialog's metadata was archived before
    if is_archived(cursor, dialog_id):
        # Get the past metadata
        cursor.execute(
            """
            SELECT dialog_id, full_request, date_of_request
            FROM dialog_metadata
            WHERE dialog_id = ?
        """,
            [dialog_id],
        )

        result = cursor.fetchone()

        # Insert it into the metadata archive
        cursor.execute(
            """
            INSERT OR IGNORE INTO dialog_metadata_archive
            (dialog_id, full_request, date_of_request)
            VALUES (?, ?, ?)
        """,
            result,
        )

    # Insert new metadata into dialog_metadata
    cursor.execute(
        "UPDATE dialog_metadata SET full_request = ?, date_of_request = ? WHERE dialog_id = ?",
        [full_request, datetime.now(timezone.utc).isoformat(), dialog_id],
    )


def insert_photo_info(
    cursor: sqlite3.Cursor, photo_info: list[tuple[int, int, str, str]]
) -> None:
    """
    A function that inserts photo data acquired from get_photo_info
    into the database.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        photo_info list[tuple(
            int (dialog id),
            int (photo id),
            str (the path where the photo was saved),
            str (photo date in iso format),
        )]
    """

    # For safety
    for row in photo_info or [()]:
        if len(row) == 0:
            continue

        cursor.execute(
            "INSERT OR IGNORE INTO dialog_photos (dialog_id, photo_id, photo_path, photo_date) VALUES (?, ?, ?, ?)",
            row,
        )


def ensure_dialog_row_exists(cursor: sqlite3.Cursor, dialog_id: int) -> None:
    """
    A function that makes sure an entry of the dialog exists
    in dialog_metadata so other functions can do their work safely.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        dialog_id (int):
            The id of the entity.
    """

    # For safety
    if not dialog_id:
        return

    cursor.execute(
        "INSERT OR IGNORE INTO dialog_metadata (dialog_id) VALUES (?)", [dialog_id]
    )


async def get_dialog_info(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
    errors_handler: Errors,
    cursor: sqlite3.Cursor,
) -> None:
    """
    A function that handles all things having to do with info, uesr ids, or metadata

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.

        errors_handler (objects.errors.Errors):
            An object that handles errors appropriately.
    """

    dialog = dialog.entity

    ensure_dialog_row_exists(cursor, dialog.id)

    full_request = await get_full_request(client, dialog, errors_handler)
    insert_info_into_appropriate_table(cursor, dialog.id, full_request)

    latest_photo_date = get_latest_photo_date(cursor, dialog.id)
    photo_info = await get_photo_info(client, dialog, errors_handler, latest_photo_date)
    insert_photo_info(cursor, photo_info)

    await add_users_to_set(client, dialog, users, errors_handler)


async def get_full_request(
    client: TelegramClient, dialog: tl.custom.dialog.Dialog, errors_handler: Errors
) -> str:
    """
    A function that gets the full request from telegram for
    the different types of dialogs.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        errors_handler (objects.errors.Errors):
            An object that handles errors appropriately.

    Retunrs:
        str:
            A srting of the full request recieved from telegram of
            the dilaog we are archiving its metadata.
    """

    try:
        full_request = None

        if isinstance(dialog, types.Channel):
            full_request = await client(
                functions.channels.GetFullChannelRequest(dialog.id)
            )

        elif isinstance(dialog, types.User):
            full_request = await client(functions.users.GetFullUserRequest(dialog.id))

        elif isinstance(dialog, types.Chat):
            full_request = await client(
                functions.messages.GetFullChatRequest(dialog.id)
            )

        else:
            logger.warning(f"Unknown dialog type: {dialog}")
            return ""

        return full_request.stringify()
    except Exception as e:
        logger.exception(f"Exception occurred : {e}")
        await errors_handler.handle(e)


async def get_photo_info(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    errors_handler: Errors,
    latest_photo_date: datetime,
) -> list[tuple[int, int, str, str]]:
    """
    A function that downloads and gets the metadata of profile
    photos of dialogs.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        errors_handler (objects.errors.Errors):
            An object that handles errors appropriately.

        latest_photo_date (datetime):
            The date of the latest photo in the database
            in case this dialog was archived before so we
            don't donwload duplicate photos and metadata.

    Returns:
        list[tuple(
            int (dialog id),
            int (photo id),
            str (the path where the photo was saved),
            str (photo date in iso format),
        )]
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
                (dialog.id, photo.id, photo_path, datetime.isoformat(photo.date))
            )

    except Exception as e:
        logger.exception(f"Exception occurred : {e}")
        await errors_handler.handle(e)

    return photo_data


async def add_users_to_set(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
    errors_handler: Errors,
) -> None:
    """
    A function that parses users in chats, and adds
    them to the accumulative set of users we have.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.

        errors_handler (objects.errors.Errors):
            An object that handles errors appropriately.
    """

    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)

    except ChatAdminRequiredError as e:
        logger.info(f"You can't parse users in this chat, it's a private chat: {e}")
        return

    except ChannelPrivateError as e:
        logger.info(
            f"You can't parse users from this channel, you are not an admin: {e}"
        )
        return

    except BadRequestError as e:
        logger.warning(f"Something went wrong, due to that we can't parse users: {e}")
        return

    except Exception as e:
        logger.exception(f"Exception occurred : {e}")
        await errors_handler.handle(e)


def insert_users_ids(cursor: sqlite3.Cursor, user: int, dialog_id: int) -> None:
    """
    A function that inserts a user's id into the database.

    Args:
        cursor (sqlite3.Cursor):
            The cursor of the database.

        user (int):
            the id of the user we want to insert their id into the database.
            Note that a user can be a channel or any other type of entity.

        dialog_id (int):
            The id of the entity where this user was found.
    """

    # For safety
    if not user or not dialog_id:
        return

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, dialog_id) VALUES (?, ?)",
        [user, dialog_id],
    )


async def entity_handler(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    users: set[int],
    errors_handler: Errors,
    cursor: sqlite3.Cursor,
    skip_details: bool = False,
) -> None:
    """
    A function that handles the metadata of entities found in dialogs.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.

        errors_handler (objects.errors.Errors):
            An object that handles errors appropriately.

        cursor (sqlite3.Cursor):
            The cursor of the database.

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
        insert_users_ids(cursor, user, dialog_id)

    # In case of a key interruption
    if skip_details:
        return

    # Get the metadata of users from the original dialog
    for user in users:
        entity = await client.get_entity(user)

        # Right now the function get_dialog_info uses
        # dialog.entity, and since there's not way to get
        # a dialog class, just do this trick
        fake_dialog = SimpleNamespace(entity=entity)

        # We pass an empty set because we don't want
        # it to function as a crawler, for now at least
        await get_dialog_info(client, fake_dialog, set(), errors_handler, cursor)
