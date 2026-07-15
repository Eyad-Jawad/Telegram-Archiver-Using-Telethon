from helpers import text
from unittest.mock import MagicMock, patch
from telethon import types
import pytest

def testReplyHandlerWithNoMessage():
    assert text.replyHandler(None, None) == 0

def testReplyHandlerWithEmptyMessage():
    message = MagicMock()
    message.reply_to = None
    assert text.replyHandler(message, None) == 0

def testReplyHandlerWithReplyToUser():
    message = MagicMock()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = None
    message.reply_to_msg_id = 10

    assert text.replyHandler(message, None) == 10

@patch("helpers.text.get_peer_id")
def testReplyHandlerWithReplyToChannel(mockGetId):
    message = MagicMock()
    users = set()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = 1
    message.reply_to_msg_id = 10

    mockGetId.return_value = 1001

    assert text.replyHandler(message, users) == "1001:10"
    assert users == {1001}
    mockGetId.assert_called_once_with(1)

def testForwardHandlerWithNoMessage():
    assert text.forwardHandler(None, None) == [0, 0]

def testForwardHandlerWithNoForward():
    message = MagicMock()
    message.forward = None
    
    assert text.forwardHandler(message, None) == [0, 0]

def testForwardHandlerWithForwardAndNoUser():
    message = MagicMock()
    forward = MagicMock

    message.forward = forward

    forward.from_name = "Me"
    forward.from_id = None

    assert text.forwardHandler(message, None) == ["Me", 0]

@patch("helpers.text.get_peer_id")
def testForwardHandlerWithForwardAndUser(mockGetId):
    message = MagicMock()
    users = set()
    forward = MagicMock

    message.forward = forward

    forward.from_name = "Me"
    forward.from_id = 1

    mockGetId.return_value = 1001

    assert text.forwardHandler(message, users) == ["Me", 1001]
    mockGetId.assert_called_once_with(1)
    assert users == {1001}

def testTextHandlerWithTextlMessage():
    message = MagicMock()
    message.text = "Noice"
    
    assert text.textHandler(message) == "Noice"

@pytest.mark.parametrize(
    ("actionType, outputMessage"),
    [
        (types.MessageActionPinMessage, "a message was pinned"), 
        (types.MessageActionChatAddUser, "Me was added"), 
        (types.MessageActionChatJoinedByLink, "1234 joined"), 
        (types.MessageActionChatDeleteUser, "4321 was kicked/left"),
        (types.MessageActionChatEditPhoto, "chat photo changed"),
        (types.MessageActionChatEditTitle, "chat title changed to Da Chat"),
        (types.MessageActionChatCreate, "Da Chat was created with users: Me"),
        (None, "MagicMock was done."),
    ],
)
def testTextHandlerWithActionMessage(actionType, outputMessage):
    message = MagicMock(spec=types.MessageService)
    message.text = None

    action = MagicMock(spec=actionType)

    action.users = "Me"
    action.inviter_id = 1234
    action.user_id = 4321
    action.title = "Da Chat"
    action.__str__.return_value = "MagicMock"

    message.action = action

    assert text.textHandler(message) == outputMessage

