from objects.dialog import Dialog
from unittest.mock import MagicMock, AsyncMock, patch, call
from telethon import types
import pytest, sqlite3, pytest_asyncio


@pytest.fixture
def mockClient():
    client = AsyncMock()

    totalMessages = MagicMock()
    totalMessages.total = 10

    client.get_messages.return_value = totalMessages

    return client


@pytest.fixture
def mockDialog():
    dialog = MagicMock()

    entity = MagicMock()
    dialog.entity = entity
    dialog.id = 1

    dialog.name = "Me"

    return dialog


@pytest.fixture
def mockConfig():
    config = MagicMock()
    config.fileSizeThresholdInBytes = 5

    return config


@pytest.fixture
def mockConnAndCursor():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    return conn, cursor


@pytest.fixture
def checkpointFixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            dialogId INTEGER,
            lastMessageId INTEGER,
            messageCounter INTEGER, 
            archivingTime FLOAT NOT NULL DEFAULT 0.0
        )
    """)

    cursor.execute("INSERT INTO dialogs (dialogId) VALUES (?)", [1])

    yield cursor

    conn.close()


@pytest.fixture
def archiveMessageFixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER,
            messageId INTEGER ,
            authorName TEXT,
            views INTEGER,
            senderId INTEGER,
            forwardFromUsername INTEGER,
            forwardFromUserId INTEGER,
            repliedToId INTEGER,
            text TEXT,
            date DATETIME,
            editDate DATETIME,
            filePath TEXT,
            fileId TEXT,
            fileSize FLOAT NOT NULL DEFAULT 0.0,
            downloadedMedia BOOL NOT NULL DEFAULT FALSE,
            UNIQUE (dialogId, messageId)
        )
    """)

    yield cursor

    conn.close()


@pytest_asyncio.fixture
@patch("objects.dialog.Dialog.getCheckpoint")
@patch("objects.dialog.file")
@patch("objects.dialog.prog")
@patch("objects.dialog.err")
@patch("helpers.sqlTables.makeTables")
@patch("objects.dialog.Dialog.getDialogType")
@patch("telethon.utils.get_peer_id")
@patch("sqlite3.connect")
@patch("logging.Logger.info")
async def mockDialogClass(
    mockLogger,
    mockConnect,
    mockGetId,
    mockGetType,
    mockMakeTables,
    mockError,
    mockProgress,
    mockFile,
    mockCheckpoint,
    mockClient,
    mockDialog,
    mockConfig,
    mockConnAndCursor,
):
    progress = MagicMock()
    file = MagicMock()
    error = MagicMock()

    mockConnect.return_value = mockConnAndCursor[0]

    mockGetId.return_value = 1
    mockGetType.return_value = "Something"

    mockError.return_value = error
    mockProgress.return_value = progress
    mockFile.return_value = file

    mockCheckpoint.return_value = [123]

    obj = Dialog(mockClient, mockConfig, mockDialog)
    await obj.setUp()

    return {
        "obj": obj,
        "mockDialog": mockDialog,
        "mockClient": mockClient,
        "mockConfig": mockConfig,
        "mockLogger": mockLogger,
        "mockConnect": mockConnect,
        "mockGetId": mockGetId,
        "mockGetType": mockGetType,
        "mockMakeTables": mockMakeTables,
        "mockConnAndCursor": mockConnAndCursor,
        "mockProgress": mockProgress,
        "progress": progress,
        "mockFile": mockFile,
        "file": file,
        "mockError": mockError,
        "mockCheckpoint": mockCheckpoint,
        "progress": progress,
    }


@pytest.mark.asyncio
async def testDialogInit(mockDialogClass):
    assert mockDialogClass["obj"].client is mockDialogClass["mockClient"]
    assert mockDialogClass["obj"].dialog is mockDialogClass["mockDialog"]
    assert mockDialogClass["obj"].entity is mockDialogClass["mockDialog"].entity
    assert mockDialogClass["obj"].config is mockDialogClass["mockConfig"]
    assert mockDialogClass["obj"].id == 1
    assert mockDialogClass["obj"].type == "Something"
    assert mockDialogClass["obj"].totalMessages == 10
    mockDialogClass["mockLogger"].assert_called_once_with("Initiating the dialog class")
    mockDialogClass["mockConnect"].assert_called_once_with("telegram.db")
    mockDialogClass["mockGetId"].assert_called_once_with(
        mockDialogClass["mockDialog"].entity
    )
    mockDialogClass["mockGetType"].assert_called_once()
    mockDialogClass["mockMakeTables"].assert_called_once_with(
        mockDialogClass["mockConnAndCursor"][1]
    )

    assert mockDialogClass["mockConnAndCursor"][1].execute.call_count == 2
    assert mockDialogClass["mockConnAndCursor"][1].execute.call_args_list == [
        call(
            "INSERT OR IGNORE INTO dialogs (dialogId, name, type) VALUES  (?, ?, ?)",
            [1, "Me", "Something"],
        ),
        call(
            "UPDATE dialogs SET totalNumberOfMessages = ? WHERE dialogId = ?",
            [10, 1],
        ),
    ]

    assert mockDialogClass["mockConnAndCursor"][0].commit.call_count == 2

    mockDialogClass["mockClient"].get_messages.assert_awaited_once_with(
        mockDialogClass["mockDialog"], limit=0
    )
    mockDialogClass["mockProgress"].assert_called_once_with(10)
    mockDialogClass["mockFile"].assert_called_once_with(5)
    mockDialogClass["mockError"].assert_called_once_with(
        1,
        mockDialogClass["mockConnAndCursor"][0],
        mockDialogClass["mockConnAndCursor"][1],
        mockDialogClass["progress"],
        mockDialogClass["file"],
        mockDialogClass["obj"],
    )
    mockDialogClass["mockCheckpoint"].assert_called_once()
    mockDialogClass["progress"].useCheckpoint.assert_called_once_with([123])
    mockDialogClass["obj"].users = set()


def testDialogGetTypeWithUser(mockDialogClass):
    obj = mockDialogClass["obj"]
    entity = MagicMock(spec=types.User)
    obj.entity = entity
    assert obj.getDialogType() == "User"


def testDialogGetTypeWithChat(mockDialogClass):
    obj = mockDialogClass["obj"]
    entity = MagicMock(spec=types.Chat)
    obj.entity = entity
    assert obj.getDialogType() == "Chat"


def testDialogGetTypeWithChannel(mockDialogClass):
    obj = mockDialogClass["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = True
    obj.entity = entity
    assert obj.getDialogType() == "Channel"


def testDialogGetTypeWithSupergroup(mockDialogClass):
    # .megagroup
    obj = mockDialogClass["obj"]
    entity = MagicMock(spec=types.Channel)
    entity.broadcast = False
    obj.entity = entity
    assert obj.getDialogType() == "Supergroup"


def testDialogGetTypeWithUnknown(mockDialogClass):
    obj = mockDialogClass["obj"]
    entity = MagicMock()
    obj.entity = entity
    assert obj.getDialogType() == "Unknown"


@patch("objects.dialog.Dialog.getCheckpoint")
@patch("time.perf_counter")
def testDialogSavecheckpoint(
    mockCounter, mockGetCheckpoint, mockDialogClass, checkpointFixture
):
    obj = mockDialogClass["obj"]
    progress = mockDialogClass["progress"]

    progress.lastMessageID = 33
    progress.messageCounter = 3

    mockCounter.return_value = 3.3
    progress.timeStart = 3.1

    obj.cursor = checkpointFixture

    mockGetCheckpoint.return_value = [None, None, 0.0]

    obj.saveCheckpoint()

    checkpointFixture.execute("SELECT * FROM dialogs")

    # Python floating point precision makes it so it's not 0.2
    assert (1, 33, 3, 0.19999999999999973) == checkpointFixture.fetchone()
    mockGetCheckpoint.assert_called_once()
    mockCounter.assert_called_once()


def testDialogGetCheckpointWithEmptyEntry(mockDialogClass, checkpointFixture):
    obj = mockDialogClass["obj"]
    obj.cursor = checkpointFixture

    assert obj.getCheckpoint() == [None, None, 0.0]


def testDialogGetCheckpointWithOneEntry(mockDialogClass, checkpointFixture):
    obj = mockDialogClass["obj"]
    obj.cursor = checkpointFixture

    checkpointFixture.execute("""
        UPDATE dialogs SET
            lastMessageId = 33,
            messageCounter = 3,
            archivingTime = 3.3
        WHERE dialogId = 1    
    """)

    assert obj.getCheckpoint() == [33, 3, 3.3]


def testDialogGetCheckpointWithManyEntry(mockDialogClass, checkpointFixture):
    obj = mockDialogClass["obj"]
    obj.cursor = checkpointFixture

    checkpointFixture.execute("""
        UPDATE dialogs SET
            lastMessageId = 33,
            messageCounter = 3,
            archivingTime = 3.3
        WHERE dialogId = 1    
    """)

    checkpointFixture.execute("INSERT INTO dialogs (dialogId) VALUES (2)")

    assert obj.getCheckpoint() == [33, 3, 3.3]


@patch("objects.dialog.Dialog.saveCheckpoint")
@patch("helpers.info.insertUsersIntoDB")
def testDialogKeyInterruptionWithNoUserInfo(
    mockInsert, mockSave, mockDialogClass, capsys
):
    obj = mockDialogClass["obj"]

    conn = mockDialogClass["mockConnAndCursor"][0]

    config = mockDialogClass["mockConfig"]
    config.userInfo = False

    obj.handleKeyInterruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mockSave.assert_called_once()
    mockInsert.assert_not_called()

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@patch("objects.dialog.Dialog.saveCheckpoint")
@patch("helpers.info.insertUsersIntoDB")
def testDialogKeyInterruptionWithOneUser(mockInsert, mockSave, mockDialogClass, capsys):
    obj = mockDialogClass["obj"]
    obj.users = {1}

    conn = mockDialogClass["mockConnAndCursor"][0]

    config = mockDialogClass["mockConfig"]
    config.userInfo = True

    obj.handleKeyInterruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mockSave.assert_called_once()
    mockInsert.assert_called_once_with(mockDialogClass["mockConnAndCursor"][1], 1, 1)

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@patch("objects.dialog.Dialog.saveCheckpoint")
@patch("helpers.info.insertUsersIntoDB")
def testDialogKeyInterruptionWithUsers(mockInsert, mockSave, mockDialogClass, capsys):
    obj = mockDialogClass["obj"]
    obj.users = {1, 2}

    conn = mockDialogClass["mockConnAndCursor"][0]

    config = mockDialogClass["mockConfig"]
    config.userInfo = True

    obj.handleKeyInterruption()

    capture = capsys.readouterr()
    assert capture.out == "\nPlease wait a moment while the saving the checkpoint\n"

    mockSave.assert_called_once()

    assert mockInsert.call_count == 2
    assert mockInsert.call_args_list == [
        call(mockDialogClass["mockConnAndCursor"][1], 1, 1),
        call(mockDialogClass["mockConnAndCursor"][1], 2, 1),
    ]

    # two calls in setup
    assert conn.commit.call_count == 3
    conn.close.assert_called_once()


@pytest.mark.asyncio
@patch("helpers.info.userIdHandler")
@patch("helpers.text.forwardHandler")
@patch("helpers.text.replyHandler")
@patch("helpers.text.textHandler")
@patch("helpers.reactions.reactionHandler", new_callable=AsyncMock)
async def testDialogArchiveMessage(
    mockReaction,
    mockText,
    mockReply,
    mockForward,
    mockUser,
    mockDialogClass,
    archiveMessageFixture,
):
    obj = mockDialogClass["obj"]
    config = mockDialogClass["mockConfig"]
    file = mockDialogClass["file"]
    progress = mockDialogClass["progress"]

    message = MagicMock()
    message.id = 33
    message.views = 600
    message.file = MagicMock()
    message.file.size = 100
    message.date = "Today"
    message.edit_date = "Just now"

    config.texts = True
    config.files = True
    config.reactions = True

    file.handle = AsyncMock()
    file.handle.return_value = ["There", "Secret", 3.0, 1]

    progress.sizeInMb = 25
    progress.MbToByte = 2

    obj.cursor = archiveMessageFixture

    mockUser.return_value = ["Me", 5]
    mockForward.return_value = ["He", 17]
    mockReply.return_value = 32
    mockText.return_value = "Noice day"

    await obj.archiveMessage(message)

    mockUser.assert_called_once_with(message, obj.users)
    mockForward.assert_called_once_with(message, obj.users)
    mockReply.assert_called_once_with(message, obj.users)
    mockText.assert_called_once_with(message)

    file.handle.assert_awaited_once_with(message)
    assert progress.sizeInMb == 75

    mockReaction.assert_awaited_once_with(
        mockDialogClass["mockClient"],
        mockDialogClass["mockDialog"],
        message,
        archiveMessageFixture,
    )

    archiveMessageFixture.execute("SELECT * FROM messages")

    assert (
        1,
        1,
        33,
        "Me",
        600,
        5,
        "He",
        17,
        32,
        "Noice day",
        "Today",
        "Just now",
        "There",
        "Secret",
        3.0,
        1,
    ) == archiveMessageFixture.fetchone()

