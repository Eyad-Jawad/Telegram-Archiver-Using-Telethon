import pytest
from helpers.text import *
from unittest.mock import MagicMock, patch
from telethon import types


def test_reply_handler_with_no_message():
    assert reply_handler(None, None) == 0


def test_reply_handler_with_empty_message():
    message = MagicMock()
    message.reply_to = None
    assert reply_handler(message, None) == 0


def test_reply_handler_with_reply_to_user():
    message = MagicMock()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = None
    message.reply_to_msg_id = 10

    assert reply_handler(message, None) == 10


def test_reply_handler_with_reply_to_private_dialog():
    message = MagicMock()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = None
    message.reply_to_msg_id = None
    message.reply_to.reply_from.from_name = "He"
    message.reply_to.quote_text = "Hi"

    assert reply_handler(message, None) == "He:Hi"


def test_reply_handler_with_reply_to_story():
    message = MagicMock()
    message.reply_to = MagicMock(spec=types.MessageReplyStoryHeader)

    assert reply_handler(message, None) == "Replied to a story"


@patch("helpers.text.get_peer_id")
def test_reply_handler_with_reply_to_channel(mock_get_id):
    message = MagicMock()
    users = set()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = 1
    message.reply_to_msg_id = 10

    mock_get_id.return_value = 1001

    assert reply_handler(message, users) == "1001:10"
    assert users == {1001}
    mock_get_id.assert_called_once_with(1)


def test_forward_handler_with_no_message():
    assert forward_handler(None, None) == ("", 0)


def test_forward_handler_with_no_forward():
    message = MagicMock()
    message.forward = None

    assert forward_handler(message, None) == ("", 0)


def test_forward_handler_with_forward_and_no_user():
    message = MagicMock()
    forward = MagicMock()

    message.forward = forward

    forward.from_name = "Me"
    forward.from_id = None

    assert forward_handler(message, None) == ("Me", 0)


@patch("helpers.text.get_peer_id")
def test_forward_handler_with_forward_and_user(mock_get_id):
    message = MagicMock()
    users = set()
    forward = MagicMock()

    message.forward = forward

    forward.from_name = "Me"
    forward.from_id = 1

    mock_get_id.return_value = 1001

    assert forward_handler(message, users) == ("Me", 1001)
    mock_get_id.assert_called_once_with(1)
    assert users == {1001}


def test_text_handler_with_text_message():
    message = MagicMock()
    message.text = "Noice"

    assert text_handler(message) == "Noice"


@pytest.mark.parametrize(
    ("action_type, output_message"),
    [
        (types.MessageActionPinMessage, "A message was pinned."),
        (types.MessageActionChatAddUser, "Me was added."),
        (types.MessageActionChatJoinedByLink, "1234 joined."),
        (types.MessageActionChatDeleteUser, "4321 was kicked/left."),
        (types.MessageActionChatEditPhoto, "Chat photo was changed."),
        (types.MessageActionChatEditTitle, "Chat title was changed to Da Chat."),
        (types.MessageActionChatCreate, "Da Chat was created with users: Me."),
        (types.MessageActionChannelCreate, "Da Chat was created."),
        (types.MessageActionHistoryClear, "Message history was cleared."),
        (types.MessageActionPhoneCall, "A video call for 10."),
        (types.MessageActionTopicEdit, "Topic was editied: Da Chat, and emoji: 12."),
        (types.MessageActionGroupCall, "A group call for 10."),
        (
            types.MessageActionInviteToGroupCall,
            "A group call invite with the users: Me",
        ),
        (types.MessageActionGroupCallScheduled, "A scheduled group call on Tomorrow."),
        (None, "MagicMock was done."),
    ],
)
def test_text_handler_with_action_message(action_type, output_message):
    message = MagicMock(spec=types.MessageService)
    message.text = None

    action = MagicMock(spec=action_type)

    action.users = "Me"
    action.inviter_id = 1234
    action.user_id = 4321
    action.title = "Da Chat"
    action.video = True
    action.duration = 10
    action.icon_emoji_id = 12
    action.schedule_date = "Tomorrow"
    action.__str__.return_value = "MagicMock"

    message.action = action

    assert text_handler(message) == output_message
