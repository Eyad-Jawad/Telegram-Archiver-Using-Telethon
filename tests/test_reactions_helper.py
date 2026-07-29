import pytest
import sqlite3
from helpers.reactions import *
from unittest.mock import MagicMock, AsyncMock, patch, call
from telethon import types


@pytest.fixture
def insert_react_fixture():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE reactions (
            dialog_id INTEGER, 
            message_id INTEGER,
            reactors_id INTEGER,
            reacting_date DATETIME,
            reaction TEXT,
            count INTEGER NOT NULL DEFAULT 1
        )
    """)

    yield cursor

    conn.close()


def test_reaction_type_with_no_react():
    assert reaction_type(None) == "No Emoji"


def test_reaction_type_with_basic_reaction():
    react = MagicMock()
    react.reaction = MagicMock(spec=types.ReactionEmoji)
    react.reaction.emoticon = "🐔"

    assert reaction_type(react) == "🐔"


def test_reaction_type_with_custom_reaction():
    react = MagicMock()
    react.reaction = MagicMock(spec=types.ReactionCustomEmoji)

    assert reaction_type(react) == "Custom Emoji"


def test_reaction_type_with_unkown_reaction():
    react = MagicMock()
    react.reaction = MagicMock()

    assert reaction_type(react) == "Unknown Emoji Type"


def test_get_peer_id_with_no_react():
    assert get_peer_id(None) == 0


def test_get_peer_id_with_user_reactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerUser)
    react.peer_id.user_id = 1

    assert get_peer_id(react) == 1


def test_get_peer_id_with_in_channel_reactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerChannel)
    react.peer_id.channel_id = 1

    assert get_peer_id(react) == 1


def test_get_peer_id_with_chat_reactor():
    react = MagicMock()
    react.peer_id = MagicMock(spec=types.PeerChat)
    react.peer_id.chat_id = 1

    assert get_peer_id(react) == 1


def test_get_peer_id_with_no_known_reactor_type():
    react = MagicMock()
    react.peer_id = MagicMock()

    assert get_peer_id(react) == 0


@pytest.mark.asyncio
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def test_get_reaction_list_with_no_input(mock_get_List):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()

    message.id = 10

    mock_get_List.return_value = "idk what"

    result = MagicMock()
    result.reactions = []
    result.next_offset = None

    client.return_value = result

    assert await get_reaction_list(client, dialog, message) == []
    mock_get_List.assert_called_once_with(
        peer=dialog, id=10, reaction=None, limit=10000, offset=None
    )
    client.assert_awaited_once_with("idk what")


@pytest.mark.asyncio
@patch("helpers.reactions.get_peer_id")
@patch("helpers.reactions.reaction_type")
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def test_get_reaction_list_with_one_reaction(
    mock_get_List, mock_reaction_type, mock_get_id
):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()
    react = MagicMock()

    dialog.id = 1

    message.id = 10

    mock_get_List.return_value = "idk what"
    mock_reaction_type.return_value = "🐔"
    mock_get_id.return_value = 5

    react.date = "Anything"

    request = MagicMock()
    request.reactions = [react]
    request.next_offset = None

    client.return_value = request

    assert await get_reaction_list(client, dialog, message) == [
        (1, 10, 5, "Anything", "🐔")
    ]

    client.assert_awaited_once_with("idk what")

    mock_get_List.assert_called_once_with(
        peer=dialog, id=10, reaction=None, limit=10000, offset=None
    )
    mock_get_id.assert_called_once_with(react)
    mock_reaction_type.assert_called_once_with(react)


@pytest.mark.asyncio
@patch("helpers.reactions.get_peer_id")
@patch("helpers.reactions.reaction_type")
@patch("telethon.functions.messages.GetMessageReactionsListRequest")
async def test_get_reaction_list_with_many_reactions(
    mock_get_List, mock_reaction_type, mock_get_id
):
    client = AsyncMock()
    dialog = MagicMock()
    message = MagicMock()
    react1 = MagicMock()
    react2 = MagicMock()

    dialog.id = 1

    message.id = 10

    mock_get_List.return_value = "idk what"
    mock_reaction_type.side_effect = ["🐔", "🐤"]
    mock_get_id.side_effect = [5, 15]

    react1.date = "Anything"
    react2.date = "Something"

    reqeust1 = MagicMock()
    reqeust2 = MagicMock()

    reqeust1.reactions = [react1]
    reqeust2.reactions = [react2]

    reqeust1.next_offset = reqeust2
    reqeust2.next_offset = None

    client.side_effect = [reqeust1, reqeust2]

    assert await get_reaction_list(client, dialog, message) == [
        (1, 10, 5, "Anything", "🐔"),
        (1, 10, 15, "Something", "🐤"),
    ]

    assert client.await_count == 2
    assert client.await_args_list == [call("idk what"), call("idk what")]

    assert mock_get_List.call_count == 2
    assert mock_get_List.call_args_list == [
        call(peer=dialog, id=10, reaction=None, limit=10000, offset=None),
        call(peer=dialog, id=10, reaction=None, limit=10000, offset=reqeust2),
    ]

    assert mock_get_id.call_count == 2
    assert mock_get_id.call_args_list == [call(react1), call(react2)]

    assert mock_reaction_type.call_count == 2
    assert mock_reaction_type.call_args_list == [call(react1), call(react2)]


@patch("helpers.reactions.reaction_type")
def test_insert_channel_reaction(mock_reaction_type, insert_react_fixture):
    cursor = insert_react_fixture
    react = MagicMock()
    react.count = 12

    mock_reaction_type.return_value = "🐔"

    insert_channel_reaction(cursor, 1, 10, react)

    cursor.execute("SELECT * FROM reactions")

    assert (1, 10, None, None, "🐔", 12) == cursor.fetchone()
    mock_reaction_type.assert_called_once_with(react)


def test_insert_chat_reaction(insert_react_fixture):
    cursor = insert_react_fixture
    result = (1, 10, 5, "Someday", "🐔")

    insert_chat_reaction(cursor, result)

    cursor.execute("SELECT * FROM reactions")

    assert (1, 10, 5, "Someday", "🐔", 1) == cursor.fetchone()


@pytest.mark.asyncio
@patch("helpers.reactions.get_reaction_list", new_callable=AsyncMock)
@patch("helpers.reactions.insert_channel_reaction")
@patch("helpers.reactions.insert_chat_reaction")
async def test_reaction_handler_with_no_message(
    mock_insert_Chat, mock_insert_Channel, mock_get_reaction
):
    await reaction_handler(None, None, None, None)

    mock_insert_Chat.assert_not_called()
    mock_insert_Channel.assert_not_called()
    mock_get_reaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.get_reaction_list", new_callable=AsyncMock)
@patch("helpers.reactions.insert_channel_reaction")
@patch("helpers.reactions.insert_chat_reaction")
async def test_reaction_handler_with_empty_reactions(
    mock_insert_Chat, mock_insert_Channel, mock_get_reaction
):
    message = MagicMock()
    message.reactions = None
    await reaction_handler(None, None, message, None)

    mock_insert_Chat.assert_not_called()
    mock_insert_Channel.assert_not_called()
    mock_get_reaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.get_reaction_list", new_callable=AsyncMock)
@patch("helpers.reactions.insert_channel_reaction")
@patch("helpers.reactions.insert_chat_reaction")
async def test_reaction_handler_with_channel_reactions(
    mock_insert_Chat, mock_insert_Channel, mock_get_reaction
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

    await reaction_handler(client, dialog, message, cursor)

    mock_insert_Channel.assert_called_once_with(cursor, 1, 10, react)
    mock_insert_Chat.assert_not_called()
    mock_get_reaction.assert_not_awaited()


@pytest.mark.asyncio
@patch("helpers.reactions.get_reaction_list", new_callable=AsyncMock)
@patch("helpers.reactions.insert_channel_reaction")
@patch("helpers.reactions.insert_chat_reaction")
async def test_reaction_handler_with_valid_chat_reactions(
    mock_insert_Chat, mock_insert_Channel, mock_get_reaction
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

    mock_get_reaction.return_value = [[1, 2, 3], []]

    await reaction_handler(client, dialog, message, cursor)

    mock_insert_Channel.assert_not_called()
    mock_insert_Chat.assert_called_once_with(cursor, [1, 2, 3])
    mock_get_reaction.assert_awaited_once_with(client, dialog, message)
