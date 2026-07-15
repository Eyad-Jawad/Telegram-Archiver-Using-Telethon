from helpers import reactions
from unittest.mock import MagicMock, AsyncMock, patch, call
from telethon import types
import pytest, sqlite3


@pytest.fixture
def insertReactFixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE reactions (
            dialogId INTEGER, 
            messageId INTEGER,
            reactorsId INTEGER,
            dateOfReacting DATETIME,
            reaction TEXT,
            count INTEGER NOT NULL DEFAULT 1
        )
    """)

    yield cursor

    conn.close()


def testReactionTypeWithNoReact():
    assert reactions.reactionType(None) == "No Emoji"


def testReactionTypeWithBasicReaction():
    react = MagicMock()
    react.reaction = MagicMock(spec=types.ReactionEmoji)
    react.reaction.emoticon = "🐔"

    assert reactions.reactionType(react) == "🐔"


def testReactionTypeWithCustomReaction():
    react = MagicMock()
    react.reaction = MagicMock(spec=types.ReactionCustomEmoji)

    assert reactions.reactionType(react) == "Custom Emoji"


def testReactionTypeWithUnkownReaction():
    react = MagicMock()
    react.reaction = MagicMock()

    assert reactions.reactionType(react) == "Unknown Emoji Type"


def testGetPeerIdWithNoReact():
    assert reactions.getPeerId(None) == 0


def testGetPeerIdWithUserReactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerUser)
    react.peer_id.user_id = 1

    assert reactions.getPeerId(react) == 1


def testGetPeerIdWithInChannelReactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerChannel)
    react.peer_id.channel_id = 1

    assert reactions.getPeerId(react) == 1


def testGetPeerIdWithChatReactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerChat)
    react.peer_id.chat_id = 1

    assert reactions.getPeerId(react) == 1


def testGetPeerIdWithNoKnownReactorType():
    react = MagicMock()
    react.peer_id = MagicMock()

    assert reactions.getPeerId(react) == 0


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def testGetReactionListWithNoInput(mockGetList):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()

    message.id = 10

    mockGetList.return_value = "Idk what"

    result = MagicMock()
    result.reactions = []
    result.next_offset = None

    client.return_value = result

    assert await reactions.getReactionList(client, dialog, message) == []
    mockGetList.assert_called_once_with(
        peer=dialog, id=10, reaction=None, limit=100, offset=None
    )
    client.assert_awaited_once_with("Idk what")


@pytest.mark.asyncio
@patch("helpers.reactions.getPeerId")
@patch("helpers.reactions.reactionType")
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def testGetReactionListWithOneReaction(mockGetList, mockReactionType, mockGetId):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()
    react = MagicMock()

    dialog.id = 1

    message.id = 10

    mockGetList.return_value = "Idk what"
    mockReactionType.return_value = "🐔"
    mockGetId.return_value = 5

    react.date = "Anything"

    request = MagicMock()
    request.reactions = [react]
    request.next_offset = None

    client.return_value = request

    assert await reactions.getReactionList(client, dialog, message) == [
        [1, 10, 5, "Anything", "🐔"]
    ]

    client.assert_awaited_once_with("Idk what")

    mockGetList.assert_called_once_with(
        peer=dialog, id=10, reaction=None, limit=100, offset=None
    )
    mockGetId.assert_called_once_with(react)
    mockReactionType.assert_called_once_with(react)


@pytest.mark.asyncio
@patch("helpers.reactions.getPeerId")
@patch("helpers.reactions.reactionType")
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def testGetReactionListWithManyReactions(
    mockGetList, mockReactionType, mockGetId
):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()
    react1 = MagicMock()
    react2 = MagicMock()

    dialog.id = 1

    message.id = 10

    mockGetList.return_value = "Idk what"
    mockReactionType.side_effect = ["🐔", "🐤"]
    mockGetId.side_effect = [5, 15]

    react1.date = "Anything"
    react2.date = "Something"

    reqeust1 = MagicMock()
    reqeust2 = MagicMock()

    reqeust1.reactions = [react1]
    reqeust2.reactions = [react2]

    reqeust1.next_offset = reqeust2
    reqeust2.next_offset = None

    client.side_effect = [reqeust1, reqeust2]

    assert await reactions.getReactionList(client, dialog, message) == [
        [1, 10, 5, "Anything", "🐔"],
        [1, 10, 15, "Something", "🐤"],
    ]

    assert client.await_count == 2
    assert client.await_args_list == [call("Idk what"), call("Idk what")]

    assert mockGetList.call_count == 2
    assert mockGetList.call_args_list == [
        call(peer=dialog, id=10, reaction=None, limit=100, offset=None),
        call(peer=dialog, id=10, reaction=None, limit=100, offset=reqeust2),
    ]

    assert mockGetId.call_count == 2
    assert mockGetId.call_args_list == [call(react1), call(react2)]

    assert mockReactionType.call_count == 2
    assert mockReactionType.call_args_list == [call(react1), call(react2)]


@patch("helpers.reactions.reactionType")
def testInsertChannelReaction(mockReactionType, insertReactFixture):
    cursor = insertReactFixture
    react = MagicMock()
    react.count = 12

    mockReactionType.return_value = "🐔"

    reactions.insertChannelReaction(cursor, 1, 10, react)

    cursor.execute("SELECT * FROM reactions")

    assert (1, 10, None, None, "🐔", 12) == cursor.fetchone()
    mockReactionType.assert_called_once_with(react)


def testInsertChatReaction(insertReactFixture):
    cursor = insertReactFixture
    result = [1, 10, 5, "Someday", "🐔"]

    reactions.insertChatReaction(cursor, result)

    cursor.execute("SELECT * FROM reactions")

    assert (1, 10, 5, "Someday", "🐔", 1) == cursor.fetchone()


@pytest.mark.asyncio
@patch("helpers.reactions.getReactionList", new_callable=AsyncMock)
@patch("helpers.reactions.insertChannelReaction")
@patch("helpers.reactions.insertChatReaction")
async def testReactionHandlerWithNoMessage(
    mockInsertChat, mockInsertChannel, mockGetReaction
):
    await reactions.reactionHandler(None, None, None, None)

    mockInsertChat.assert_not_called()
    mockInsertChannel.assert_not_called()
    mockGetReaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.getReactionList", new_callable=AsyncMock)
@patch("helpers.reactions.insertChannelReaction")
@patch("helpers.reactions.insertChatReaction")
async def testReactionHandlerWithEmptyReactions(
    mockInsertChat, mockInsertChannel, mockGetReaction
):
    message = MagicMock()
    message.reactions = None
    await reactions.reactionHandler(None, None, message, None)

    mockInsertChat.assert_not_called()
    mockInsertChannel.assert_not_called()
    mockGetReaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.getReactionList", new_callable=AsyncMock)
@patch("helpers.reactions.insertChannelReaction")
@patch("helpers.reactions.insertChatReaction")
async def testReactionHandlerWithChannelReactions(
    mockInsertChat, mockInsertChannel, mockGetReaction
):
    client = MagicMock()
    dialog = MagicMock()
    message = MagicMock()
    cursor = MagicMock()

    dialog.id = 1
    message.id = 10

    result = MagicMock()

    react = MagicMock()

    result.can_see_list = False
    result.results = [react]

    message.reactions = result

    await reactions.reactionHandler(client, dialog, message, cursor)

    mockInsertChannel.assert_called_once_with(cursor, 1, 10, react)
    mockInsertChat.assert_not_called()
    mockGetReaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.getReactionList", new_callable=AsyncMock)
@patch("helpers.reactions.insertChannelReaction")
@patch("helpers.reactions.insertChatReaction")
async def testReactionHandlerWithValidChatReactions(
    mockInsertChat, mockInsertChannel, mockGetReaction
):
    client = MagicMock()
    dialog = MagicMock()
    message = MagicMock()
    cursor = MagicMock()

    result = MagicMock()

    react = MagicMock()

    result.can_see_list = True
    result.results = [react]

    message.reactions = result

    mockGetReaction.return_value = [[1, 2, 3], []]

    await reactions.reactionHandler(client, dialog, message, cursor)

    mockInsertChannel.assert_not_called()
    mockInsertChat.assert_called_once_with(cursor, [1, 2, 3])
    mockGetReaction.assert_awaited_once_with(client, dialog, message)
