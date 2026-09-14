from unittest.mock import MagicMock, patch

import pytest
from telethon import types

from helpers.text import *


@pytest.mark.asyncio
async def test_reply_handler_with_no_message(
    mock_message, check_db_msg_defaults
):
    reply_handler(None, mock_message, None)
    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_reply_handler_with_empty_message(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.reply_to = None
    reply_handler(message, mock_message, None)
    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_reply_handler_with_reply_to_user(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = None
    message.reply_to_msg_id = 10
    message.reply_to.quote_text = "Noice"

    reply_handler(message, mock_message, None)

    await check_db_msg_defaults(
        mock_message, skips=("replied_to_id", "replied_to_text")
    )
    assert mock_message.replied_to_id == 10
    assert mock_message.replied_to_text == "Noice"


@pytest.mark.asyncio
async def test_reply_handler_with_reply_to_private_dialog(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = None
    message.reply_to_msg_id = None
    message.reply_to.reply_from.from_name = "He"
    message.reply_to.quote_text = "Hi"

    reply_handler(message, mock_message, None)

    await check_db_msg_defaults(mock_message, skips=("replied_to_text"))
    assert mock_message.replied_to_text == "He:Hi"


@pytest.mark.asyncio
async def test_reply_handler_with_reply_to_story(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.reply_to = MagicMock(spec=types.MessageReplyStoryHeader)

    reply_handler(message, mock_message, None)

    await check_db_msg_defaults(mock_message, skips=("replied_to_text"))
    assert mock_message.replied_to_text == "Replied to a story"


@pytest.mark.asyncio
@patch("helpers.text.get_peer_id")
async def test_reply_handler_with_reply_to_channel(
    mock_get_id, mock_message, check_db_msg_defaults
):
    message = MagicMock()
    users = set()
    message.reply_to = MagicMock()
    message.reply_to.reply_to_peer_id = 1
    message.reply_to_msg_id = 10
    message.reply_to.quote_text = "Noice"

    mock_get_id.return_value = 1001

    reply_handler(message, mock_message, users)

    await check_db_msg_defaults(
        mock_message,
        skips=("replied_to_id", "replied_to_entity_id", "replied_to_text"),
    )
    assert mock_message.replied_to_id == 10
    assert mock_message.replied_to_entity_id == 1001
    assert mock_message.replied_to_text == "Noice"

    assert users == {1001}
    mock_get_id.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_forward_handler_with_no_message(
    mock_message, check_db_msg_defaults
):
    forward_handler(None, mock_message, None)
    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_forward_handler_with_no_forward(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.forward = None

    forward_handler(message, mock_message, None)
    await check_db_msg_defaults(mock_message)


@pytest.mark.asyncio
async def test_forward_handler_with_forward_and_no_user(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    forward = MagicMock()

    message.forward = forward

    forward.from_name = "Me"

    forward_handler(message, mock_message, None)
    assert mock_message.forward_from_username == "Me"
    await check_db_msg_defaults(mock_message, skips=("forward_from_username"))


@pytest.mark.asyncio
@patch("helpers.text.get_peer_id")
async def test_forward_handler_with_forward_and_user(
    mock_get_id, mock_message, check_db_msg_defaults
):
    message = MagicMock()
    users = set()
    forward = MagicMock()

    message.forward = forward

    forward.from_name = "Me"
    forward.from_id = 1

    mock_get_id.return_value = 1001

    forward_handler(message, mock_message, users)

    assert mock_message.forward_from_username == "Me"
    assert mock_message.forward_from_user_id == 1001
    await check_db_msg_defaults(
        mock_message, skips=("forward_from_username", "forward_from_user_id")
    )

    mock_get_id.assert_called_once_with(1)
    assert users == {1001}


@pytest.mark.asyncio
async def test_text_handler_with_text_message(
    mock_message, check_db_msg_defaults
):
    message = MagicMock()
    message.text = "Noice"

    text_handler(message, mock_message)

    await check_db_msg_defaults(mock_message, skips="text")
    assert mock_message.text == "Noice"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_type, output_message"),
    [
        (types.MessageActionPinMessage, "A message was pinned."),
        (types.MessageActionChatAddUser, "Me was added."),
        (types.MessageActionChatJoinedByLink, "1234 joined."),
        (types.MessageActionChatDeleteUser, "4321 was kicked/left."),
        (types.MessageActionChatEditPhoto, "Chat photo was changed."),
        (
            types.MessageActionChatEditTitle,
            "Chat title was changed to Da Chat.",
        ),
        (types.MessageActionChatCreate, "Da Chat was created with users: Me."),
        (types.MessageActionChannelCreate, "Da Chat was created."),
        (types.MessageActionHistoryClear, "Message history was cleared."),
        (types.MessageActionPhoneCall, "A video call for 10."),
        (
            types.MessageActionTopicEdit,
            "Topic was editied: Da Chat, and emoji: 12.",
        ),
        (types.MessageActionGroupCall, "A group call for 10."),
        (
            types.MessageActionInviteToGroupCall,
            "A group call invite with the users: Me",
        ),
        (
            types.MessageActionGroupCallScheduled,
            "A scheduled group call on Tomorrow.",
        ),
        (None, "MagicMock was done."),
    ],
)
async def test_text_handler_with_action_message(
    action_type, output_message, mock_message, check_db_msg_defaults
):
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

    text_handler(message, mock_message)

    await check_db_msg_defaults(mock_message, skips="text")
    assert mock_message.text == output_message
