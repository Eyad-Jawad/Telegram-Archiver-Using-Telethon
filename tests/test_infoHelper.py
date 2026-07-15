from helpers import info
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from telethon import types
import pytest, sqlite3


@pytest.fixture
def cursor():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    yield cursor

    conn.close()

@pytest.fixture
def latestPhotFixture(cursor):
    cursor.execute("""
        CREATE TABLE dialogPhotos (
            dialogId INTEGER,
            photoDate DATETIME
        )
    """)

    return cursor

@pytest.fixture
def isArchivedFixture(cursor):
    cursor.execute("""
        CREATE TABLE dialogInfo (
            dialogId INTEGER UNIQUE,
            fullRequest TEXT
        )
    """)

    return cursor

@pytest.fixture
def pushInfoFixture(isArchivedFixture):
    cursor = isArchivedFixture

    cursor.execute("""
        CREATE TABLE dialogInfoArchive (
            dialogId INTEGER,
            fullRequest TEXT
        )
    """
    )

    return cursor

@pytest.fixture
def pushPhotosFixture(cursor):
    cursor.execute("""
        CREATE TABLE dialogPhotos (
            dialogId INTEGER,
            photoId INTEGER,
            photoPath TEXT,
            photoDate DATETIME
        )
    """)

    return cursor

@pytest.fixture
def insertUsersFixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            userId INTEGER,
            dialogId INTEGER,
            UNIQUE(userId, dialogId)
        )
    """)

    yield cursor

    conn.close()

@pytest.mark.parametrize(
    "postAuthorInput",
    ["eyad", "EYAD", "\\//\\//", "12", "🥀something"],
)
def testUserIdHanderWithPostAuthor(postAuthorInput):
    message = MagicMock()
    message.post_author = postAuthorInput
    usersSet = set()

    assert info.userIdHandler(message, usersSet) == [postAuthorInput, 0]
    assert len(usersSet) == 0

def testUserIdHanderWithSenderId():
    message = MagicMock()
    message.post_author = None
    message.sender_id = 1234

    assert info.userIdHandler(message, set()) == [0, 1234]

def testUserIdHanderWithNoSenderId():
    message = MagicMock()
    message.post_author = None
    message.sender_id = None

    assert info.userIdHandler(message, set()) == [0, 0]

def testUserIdHanderForUsersSet():
    usersSet = set()

    message = MagicMock()
    message.post_author = None
    message.sender_id = 1234

    info.userIdHandler(message, usersSet)

    assert usersSet == {1234}

    message.sender_id = 4321

    info.userIdHandler(message, usersSet)

    assert usersSet == {1234, 4321}

    info.userIdHandler(message, usersSet)

    assert usersSet == {1234, 4321}
    
def dateConsts():
    return [
        datetime(1900, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 10, 10, 10, 10, tzinfo=timezone.utc),
        datetime(2026, 5, 10, 10, 10, 10, tzinfo=timezone.utc),
        datetime(2026, 10, 10, 10, 10, 10, tzinfo=timezone.utc),
    ]

def testGetLatestPhotoDateForEmptyDB(latestPhotFixture):
    assert info.getLatestPhotoDate(latestPhotFixture, 21) == dateConsts()[0]

def testGetLatestPhotoDateForEmptyEntry(latestPhotFixture):
    cursor = latestPhotFixture

    cursor.execute("INSERT INTO dialogPhotos (dialogId) VALUES (?)", [1])
    assert info.getLatestPhotoDate(cursor, 1) == dateConsts()[0]
    
def testGetLatestPhotoDateForOneEntry(latestPhotFixture):
    cursor = latestPhotFixture

    DATES = dateConsts()

    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [1, datetime.isoformat(DATES[1])])
    assert info.getLatestPhotoDate(cursor, 1) == DATES[1]

def testGetLatestPhotoDateForManyDates(latestPhotFixture):
    cursor = latestPhotFixture

    DATES = dateConsts()

    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [1, datetime.isoformat(DATES[1])])
    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [1, datetime.isoformat(DATES[2])])
    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [1, datetime.isoformat(DATES[3])])

    assert info.getLatestPhotoDate(cursor, 1) == DATES[3]

def testGetLatestPhotoDateForManyEntries(latestPhotFixture):
    cursor = latestPhotFixture

    DATES = dateConsts()

    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [1, datetime.isoformat(DATES[1])])
    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [2, datetime.isoformat(DATES[2])])
    cursor.execute("INSERT INTO dialogPhotos (dialogId, photoDate) VALUES (?, ?)", [3, datetime.isoformat(DATES[3])])

    assert info.getLatestPhotoDate(cursor, 1) == DATES[1]

def testIsArchivedForEmptyDB(isArchivedFixture):
    assert info.isArchived(isArchivedFixture, 123) == False

@pytest.mark.parametrize(
    ("fullRequest, output"),
    [(None, False), ("Chickens", True)],
)
def testIsArchivedForOneEntry(isArchivedFixture, fullRequest, output):
    cursor = isArchivedFixture

    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [1, fullRequest])
    assert info.isArchived(cursor, 1) == output

def testIsArchivedForManyEntries(isArchivedFixture):
    cursor = isArchivedFixture

    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [1, None])
    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [2, None])
    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [3, "Chickens"])
    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [4, "Chicken Wings"])
    assert info.isArchived(cursor, 1) == False
    assert info.isArchived(cursor, 3) == True

def testPushInfoNotArchived(pushInfoFixture):
    cursor = pushInfoFixture

    cursor.execute("INSERT INTO dialogInfo (dialogId) VALUES (?)", [1])
    info.pushInfoIntoAppropriateTable(cursor, 1, "Chickens")

    cursor.execute("SELECT fullRequest FROM dialogInfo WHERE dialogId = 1")

    assert "Chickens" == cursor.fetchone()[0]

def testPushInfoArchived(pushInfoFixture):
    cursor = pushInfoFixture

    cursor.execute("INSERT INTO dialogInfo (dialogId, fullRequest) VALUES (?, ?)", [1, "Chickens"])
    info.pushInfoIntoAppropriateTable(cursor, 1, "Chicken wings")

    cursor.execute("SELECT fullRequest FROM dialogInfo WHERE dialogId = 1")

    assert "Chickens" == cursor.fetchone()[0]

    cursor.execute("SELECT fullRequest FROM dialogInfoArchive WHERE dialogId = 1")

    assert "Chicken wings" == cursor.fetchone()[0]

@pytest.mark.parametrize(
    ("photoData"),
    [None, [], [[]]],
)
def testPushPhotosInfoWithNothing(pushPhotosFixture, photoData):
    cursor = pushPhotosFixture
    info.pushPhotosInfo(cursor, photoData)
    
    cursor.execute("SELECT * FROM dialogPhotos")

    assert None == cursor.fetchone()

def testPushPhotosInfoWithOneEntry(pushPhotosFixture):
    cursor = pushPhotosFixture

    photoInfo = [(1, 1231, "Somewhere", "Sqlite parses time as str anyway")]

    info.pushPhotosInfo(cursor, photoInfo)

    cursor.execute("SELECT * FROM dialogPhotos")

    assert photoInfo == (cursor.fetchall())

def testPushPhotosInfoWithManyEntries(pushPhotosFixture):
    cursor = pushPhotosFixture

    photoInfo = [
        (1, 1234, "somewhere", "idk"),
        (1, 2314, "somewhere", "idk"),
        (1, 4321, "somewhere", "idk"),
    ]

    info.pushPhotosInfo(cursor, photoInfo)

    cursor.execute("SELECT * FROM dialogPhotos")

    assert photoInfo == (cursor.fetchall())

@pytest.mark.parametrize(
    "dialogId, output",
    [(1, (1, None)), (None, None)]
)
def testEnsureDialogRowExistsWithNoRow(isArchivedFixture, dialogId, output):
    cursor = isArchivedFixture

    info.ensureDialogRowExists(cursor, dialogId)

    cursor.execute("SELECT * FROM dialogInfo")

    assert output == cursor.fetchone()

def testEnsureDialogRowExistsWithOneRow(isArchivedFixture):
    cursor = isArchivedFixture

    cursor.execute("INSERT INTO dialogInfo (dialogId) VALUES (1)")

    info.ensureDialogRowExists(cursor, 1)

    cursor.execute("SELECT * FROM dialogInfo")

    assert (1, None) == cursor.fetchone()

@pytest.mark.asyncio
@patch("helpers.info.ensureDialogRowExists")
@patch("helpers.info.getFullRequest", new_callable=AsyncMock)
@patch("helpers.info.pushInfoIntoAppropriateTable")
@patch("helpers.info.getLatestPhotoDate") 
@patch("helpers.info.getPhotoInfo", new_callable=AsyncMock)
@patch("helpers.info.pushPhotosInfo")
@patch("helpers.info.addUsersToSet", new_callable=AsyncMock)
async def testGetDialogInfo(mockAddUsers, mockPushPhoto, mockGetPhoto, mockGetLatest, mockPushInto, mockFullRequest, mockEnsure):
    client = MagicMock()
    dialog = MagicMock()
    dialog.entity = MagicMock()
    dialog.entity.id = 1
    users = set()
    errorHandler = AsyncMock()
    cursor = MagicMock()

    errorHandler.handle = AsyncMock()

    fullRequest = mockFullRequest.return_value
    latestPhotoDate = mockGetLatest.return_value
    photoInfo = mockGetPhoto.return_value

    await info.getDialogInfo(client, dialog, users, errorHandler, cursor)

    mockAddUsers.assert_awaited_once_with(client, dialog.entity, users, errorHandler)
    mockPushPhoto.assert_called_once_with(cursor, photoInfo)
    mockGetPhoto.assert_awaited_once_with(client, dialog.entity, errorHandler, latestPhotoDate)
    mockGetLatest.assert_called_once_with(cursor, 1)
    mockPushInto.assert_called_once_with(cursor, 1, fullRequest)
    mockFullRequest.assert_awaited_once_with(client, dialog.entity, errorHandler)
    mockEnsure.assert_called_once_with(cursor, 1)
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
@patch("telethon.functions.channels.GetFullChannelRequest")
async def testGetFullRequestForChannel(mockChannel):
    client = AsyncMock()
    dialog = MagicMock(spec=types.Channel)
    errorHandler = AsyncMock()
    result = MagicMock()

    errorHandler.handle = AsyncMock()

    mockChannel.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result
    
    assert await info.getFullRequest(client, dialog, errorHandler) == "Chickens"
    mockChannel.assert_called_once_with(dialog)
    client.assert_awaited_once_with("Test")
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
@patch("telethon.functions.users.GetFullUserRequest")
async def testGetFullRequestForUser(mockUser):
    client = AsyncMock()
    dialog = MagicMock(spec=types.User)
    errorHandler = AsyncMock()
    result = MagicMock()

    errorHandler.handle = AsyncMock()

    mockUser.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result
    
    assert await info.getFullRequest(client, dialog, errorHandler) == "Chickens"
    mockUser.assert_called_once_with(dialog)
    client.assert_awaited_once_with("Test")
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
@patch("telethon.functions.messages.GetFullChatRequest")
async def testGetFullRequestForChat(mockChat):
    client = AsyncMock()
    dialog = MagicMock(spec=types.Chat)
    errorHandler = AsyncMock()
    result = MagicMock()

    errorHandler.handle = AsyncMock()

    mockChat.return_value = "Test"

    result.stringify.return_value = "Chickens"
    client.return_value = result
    
    assert await info.getFullRequest(client, dialog, errorHandler) == "Chickens"
    mockChat.assert_called_once_with(dialog)
    client.assert_awaited_once_with("Test")
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
@patch("telethon.functions.messages.GetFullChatRequest")
async def testGetFullRequestForError(chatMock):
    client = AsyncMock(side_effect=RuntimeError("Idk what"))
    dialog = MagicMock(spec=types.Chat)
    errorHandler = MagicMock()
    errorHandler.handle = AsyncMock()
    
    await info.getFullRequest(client, dialog, errorHandler)

    client.assert_awaited_once()
    chatMock.assert_called_once_with(dialog)
    errorHandler.handle.assert_awaited_once_with(client.side_effect, info.getFullRequest)

@pytest.mark.asyncio
async def testGetPhotoInfoForEmptyInput():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()

    errorHandler.handle = AsyncMock()

    iterator = MagicMock()
    iterator.__aiter__.return_value = []

    client.iter_profile_photos = MagicMock(return_value=iterator)

    assert await info.getPhotoInfo(client, dialog, errorHandler, None) == []
    client.iter_profile_photos.assert_called_once_with(dialog)
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
async def testGetPhotoInfoForOneInput():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    photo = MagicMock()

    DATES = dateConsts()

    dialog.id = 1

    photo.id = 5
    photo.date = DATES[2]

    iterator = MagicMock()
    iterator.__aiter__.return_value = [photo]

    client.iter_profile_photos = MagicMock(return_value=iterator)

    client.download_media = AsyncMock()
    client.download_media.return_value = "Noice"

    errorHandler.handle = AsyncMock()

    assert await info.getPhotoInfo(client, dialog, errorHandler, DATES[1]) == [[1, 5, "Noice", "2026-05-10T10:10:10+00:00"]]
    client.iter_profile_photos.assert_called_once_with(dialog)
    client.download_media.assert_awaited_once_with(photo, file="Media/")
    errorHandler.handle.assert_not_awaited()

@pytest.mark.asyncio
async def testGetPhotoInfoForError():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()

    error = RuntimeError("dunno")

    client.iter_profile_photos = MagicMock(side_effect=error)

    errorHandler.handle = AsyncMock()

    assert await info.getPhotoInfo(client, dialog, errorHandler, None) == []
    client.iter_profile_photos.assert_called_once_with(dialog)
    errorHandler.handle.assert_awaited_once_with(error, info.getPhotoInfo)

@pytest.mark.asyncio
async def testAddUsersToSetWithEmptyInput():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    users = set()

    errorHandler.handle = AsyncMock()

    iterator = MagicMock()
    iterator.__aiter__.return_value = []

    client.iter_participants.return_value = iterator

    await info.addUsersToSet(client, dialog, users, errorHandler)

    client.iter_participants.assert_called_once_with(dialog)
    errorHandler.handle.assert_not_awaited()
    assert users == set()

@pytest.mark.asyncio
async def testAddUsersToSetWithOneInput():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    users = set()

    errorHandler.handle = AsyncMock()

    user = MagicMock()
    user.id = 1

    iterator = MagicMock()
    iterator.__aiter__.return_value = [user]

    client.iter_participants.return_value = iterator

    await info.addUsersToSet(client, dialog, users, errorHandler)

    client.iter_participants.assert_called_once_with(dialog)
    errorHandler.handle.assert_not_awaited()
    assert users == {1}

@pytest.mark.asyncio
async def testAddUsersToSetWithManyInputs():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    users = {1, 5}

    errorHandler.handle = AsyncMock()

    user1 = MagicMock()
    user1.id = 1

    user2 = MagicMock()
    user2.id = 2

    user3 = MagicMock()
    user3.id = 3

    user4 = MagicMock()
    user4.id = 4

    iterator = MagicMock()
    iterator.__aiter__.return_value = [user1, user2, user3, user4]

    client.iter_participants.return_value = iterator

    await info.addUsersToSet(client, dialog, users, errorHandler)

    client.iter_participants.assert_called_once_with(dialog)
    errorHandler.handle.assert_not_awaited()
    assert users == {1, 2, 3, 4, 5}

@pytest.mark.asyncio
async def testAddUsersToSetForError():
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()

    errorHandler.handle = AsyncMock()

    error = RuntimeError("Dunno")

    client.iter_participants = MagicMock(side_effect=error)

    await info.addUsersToSet(client, dialog, None, errorHandler)

    client.iter_participants.assert_called_once_with(dialog)
    errorHandler.handle.assert_awaited_once_with(error, info.addUsersToSet)

def testInsertUsersWithNoEntry(insertUsersFixture):
    cursor = insertUsersFixture

    info.insertUsersIntoDB(cursor, None, 1)
    info.insertUsersIntoDB(cursor, 1, None)
    info.insertUsersIntoDB(cursor, None, None)

    cursor.execute("SELECT * FROM users")

    assert None == cursor.fetchone()

def testInsertUsersWithOneEntry(insertUsersFixture):
    cursor = insertUsersFixture

    info.insertUsersIntoDB(cursor, 1, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12)] == cursor.fetchall()

def testInsertUsersWithManyEntreis(insertUsersFixture):
    cursor = insertUsersFixture

    info.insertUsersIntoDB(cursor, 1, 12)
    info.insertUsersIntoDB(cursor, 1, 11)
    info.insertUsersIntoDB(cursor, 2, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12), (1, 11), (2, 12)] == cursor.fetchall()

def testInsertUsersDuplicate(insertUsersFixture):
    cursor = insertUsersFixture

    info.insertUsersIntoDB(cursor, 1, 12)

    cursor.execute("SELECT * FROM users")

    assert [(1, 12)] == cursor.fetchall()

    info.insertUsersIntoDB(cursor, 1, 12)

    assert [[]] == [cursor.fetchall()] # It's empty because it the db just fetched

@pytest.mark.asyncio
@patch("helpers.info.insertUsersIntoDB")
@patch("helpers.info.getDialogInfo", new_callable=AsyncMock)
async def testUsersHandlerWithEmptySet(mockInfo, mockInsert):
    await info.usersHandler(None, None, set(), None, None, True)

    mockInfo.assert_not_awaited()
    mockInsert.assert_not_called()

@pytest.mark.asyncio
@patch("helpers.info.insertUsersIntoDB")
@patch("helpers.info.getDialogInfo", new_callable=AsyncMock)
async def testUsersHandlerWithOneEntryAndSkip(mockInfo, mockInsert):
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    cursor = MagicMock()
    users = {5}

    dialog.entity.id = 1
    await info.usersHandler(client, dialog, users, errorHandler, cursor, True)

    mockInsert.assert_called_once_with(cursor, 5, 1)
    mockInfo.assert_not_awaited()

@pytest.mark.asyncio
@patch("helpers.info.insertUsersIntoDB")
@patch("helpers.info.getDialogInfo", new_callable=AsyncMock)
async def testUsersHandlerWithOneEntryAndNoSkip(mockInfo, mockInsert):
    client = MagicMock()
    dialog = MagicMock()
    errorHandler = MagicMock()
    cursor = MagicMock()
    users = {5}

    dialog.entity.id = 1
    await info.usersHandler(client, dialog, users, errorHandler, cursor, False)

    mockInsert.assert_called_once_with(cursor, 5, 1)
    mockInfo.assert_awaited_once_with(client, dialog, users, errorHandler, cursor)

