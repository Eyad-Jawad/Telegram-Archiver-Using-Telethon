import sqlite3
from telethon import functions, types, custom
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError
from objects import errors
from datetime import datetime, timezone


def userIdHandler(message: custom.message.Message, users: set[int]) -> list[str | int]:
    # check for the id of the user to add to the message
    if message.post_author:
        return [message.post_author, 0]

    elif not message.sender_id:
        return [0, 0]

    # check if the sender is not saved
    if message.sender_id not in users:
        users.add(message.sender_id)

    return [0, message.sender_id]


def getLatestPhotoDate(cursor: sqlite3.Cursor, dialogId: int) -> datetime:
    # format: 2026-03-06 17:45:25+00:00

    cursor.execute(
        "SELECT MAX(photoDate) FROM dialogPhotos WHERE dialogId = ?", [dialogId]
    )

    query = cursor.fetchone()
    if not query or not query[0]:
        return datetime(1900, 1, 1, tzinfo=timezone.utc)  # arbitrary date
    else:
        return datetime.fromisoformat(query[0])


def isArchived(cursor: sqlite3.Cursor, dialogId: int) -> bool:
    cursor.execute("SELECT fullRequest FROM dialogInfo WHERE dialogId = ?", [dialogId])

    query = cursor.fetchone()

    return bool(query and query[0])


def pushInfoIntoAppropriateTable(
    cursor: sqlite3.Cursor, dialogId: int, fullRequest: str
) -> None:
    if isArchived(cursor, dialogId):
        cursor.execute(
            "INSERT OR IGNORE INTO dialogInfoArchive (dialogId, fullRequest) VALUES (?, ?)",
            [dialogId, fullRequest],
        )

    else:
        cursor.execute(
            "UPDATE dialogInfo SET fullRequest = ? WHERE dialogId = ?",
            [fullRequest, dialogId],
        )


def pushPhotosInfo(cursor: sqlite3.Cursor, photosInfo: list[list[str | int]]) -> None:
    for row in photosInfo or [[]]:
        if len(row) == 0:
            continue

        cursor.execute(
            "INSERT OR IGNORE INTO dialogPhotos (dialogId, photoId, photoPath, photoDate) VALUES (?, ?, ?, ?)",
            row,
        )


def ensureDialogRowExists(cursor: sqlite3.Cursor, dialogId: int) -> None:
    if not dialogId:
        return

    cursor.execute("INSERT OR IGNORE INTO dialogInfo (dialogId) VALUES (?)", [dialogId])


async def getDialogInfo(
    client, dialog, users: set[int], errorHandler: errors.Errors, cursor: sqlite3.Cursor
) -> None:
    dialog = dialog.entity

    ensureDialogRowExists(cursor, dialog.id)

    fullRequest = await getFullRequest(client, dialog, errorHandler)
    pushInfoIntoAppropriateTable(cursor, dialog.id, fullRequest)

    latestPhotoDate = getLatestPhotoDate(cursor, dialog.id)
    photosInfo = await getPhotoInfo(client, dialog, errorHandler, latestPhotoDate)
    pushPhotosInfo(cursor, photosInfo)

    await addUsersToSet(client, dialog, users, errorHandler)


async def getFullRequest(client, dialog, errorHandler: errors.Errors) -> str:
    try:
        fullRequest = None

        if isinstance(dialog, types.Channel):
            fullRequest = await client(functions.channels.GetFullChannelRequest(dialog))

        elif isinstance(dialog, types.User):
            fullRequest = await client(functions.users.GetFullUserRequest(dialog))

        else:
            fullRequest = await client(functions.messages.GetFullChatRequest(dialog))

        return fullRequest.stringify()
    except Exception as e:
        await errorHandler.handle(e, getFullRequest)


async def getPhotoInfo(
    client, dialog, errorHandler: errors.Errors, latestPhotoDate: datetime
) -> list[list[str | int]]:
    PATH = "Media/"
    photoDataRow = []

    try:
        async for photo in client.iter_profile_photos(dialog):
            if photo.date < latestPhotoDate:
                continue

            photoPath = await client.download_media(photo, file=PATH)
            photoDataRow.append(
                [dialog.id, photo.id, photoPath, datetime.isoformat(photo.date)]
            )

    except Exception as e:
        await errorHandler.handle(e, getPhotoInfo)

    return photoDataRow


async def addUsersToSet(
    client, dialog, users: set[int], errorHandler: errors.Errors
) -> None:
    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)

    except (ChatAdminRequiredError, ChannelPrivateError, Exception) as e:
        await errorHandler.handle(e, addUsersToSet)


def insertUsersIntoDB(cursor: sqlite3.Cursor, user: int, dialogId: int) -> None:
    if not user or not dialogId:
        return

    cursor.execute(
        "INSERT OR IGNORE INTO users (userId, dialogId) VALUES (?, ?)", [user, dialogId]
    )


async def usersHandler(
    client,
    dialog,
    users: set[int],
    errorHandler: errors.Errors,
    cursor: sqlite3.Cursor,
    skipDetails: bool = False,
) -> None:
    if not users:
        return

    dialogId = dialog.entity.id

    for user in users:
        insertUsersIntoDB(cursor, user, dialogId)

    if not skipDetails:
        for user in users:
            await getDialogInfo(client, dialog, users, errorHandler, cursor)
