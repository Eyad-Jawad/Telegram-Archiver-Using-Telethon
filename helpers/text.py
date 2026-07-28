import logging
from telethon import types, custom
from telethon.utils import get_peer_id

logger = logging.getLogger(__name__)


def reply_handler(message: custom.message.Message, users: set[int]) -> str | int:
    """
    A function that handles message replies. It has many edge cases:
    reply to user, reply to private chat, reply to channel, and perhaps more.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.

    Returns:
        int | str:
            int in case of normal user id, and str in
            all the other cases.
    """

    # check if this message is a reply to another
    try:
        # for safety
        if not message or not message.reply_to:
            return 0

        # check if it's from a user or a channel
        replied_to = message.reply_to

        # What to do with a reply to a story
        # temp solution unitl I make some stuff for stories
        if isinstance(replied_to, types.MessageReplyStoryHeader):
            return "Replied to a story"

        if not (replied_to and replied_to.reply_to_peer_id):
            # This case is for replies from private dialogs
            if not message.reply_to_msg_id:
                return f"{message.reply_to.reply_from.from_name}:{message.reply_to.quote_text}"

            return message.reply_to_msg_id

        # if it's from a channel
        replied_to_id = get_peer_id(replied_to.reply_to_peer_id)

        if replied_to_id not in users:
            users.add(replied_to_id)

        return f"{replied_to_id}:{message.reply_to_msg_id}"

    except Exception as e:
        logger.exception(f"Exception occurred : {e}")
        return 0


def forward_handler(
    message: custom.message.Message, users: set[int]
) -> tuple[str, int]:
    """
    A function that handles forwarded messages from users with
    hidden or shown profiles, and from other enitities like channels.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.

    Returns:
        Tuple (
            str (The name of the entity forwarded from.),
            int (The id the entity forwarded from, if it exists.)
        )
    """

    try:
        # For safety.
        if not message or not message.forward:
            return ("", 0)

        forward = message.forward

        forward_from_name = f"{forward.from_name}"
        # Users who have their profile hidden, or
        # private channels have their id also hidden.
        if not forward.from_id:
            return (forward_from_name, 0)

        entity = forward.from_id
        peer_id = get_peer_id(entity)

        if peer_id not in users:
            users.add(peer_id)

        return (forward_from_name, peer_id)

    except Exception as e:
        logger.exception(f"Exception occurred : {e}")
        return ("", 0)


def text_handler(message: custom.message.Message) -> str:
    """
    A function that handles text messages, as well as actions
    if the message happens not to be a text message.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

    Returns:
        str:
            a string of the text message, or a string
            describing the action.
    """

    action_handlers = {
        types.MessageActionPinMessage: lambda a: "A message was pinned.",
        types.MessageActionChatAddUser: lambda a: f"{a.users} was added.",
        types.MessageActionChatJoinedByLink: lambda a: f"{a.inviter_id} joined.",
        types.MessageActionChatJoinedByRequest: lambda a: "A user joined by request.",
        types.MessageActionChatDeleteUser: lambda a: f"{a.user_id} was kicked/left.",
        types.MessageActionChatEditPhoto: lambda a: f"Chat photo was changed.",
        types.MessageActionChatDeletePhoto: lambda a: "Chat photo was deleted.",
        types.MessageActionChatEditTitle: lambda a: f"Chat title was changed to {a.title}.",
        types.MessageActionChatCreate: lambda a: f"{a.title} was created with users: {a.users}.",
        types.MessageActionChannelCreate: lambda a: f"{a.title} was created.",
        types.MessageActionHistoryClear: lambda a: "Message history was cleared.",
        types.MessageActionPhoneCall: lambda a: f"A {"video" if a.video else ""} call for {a.duration}.",
        types.MessageActionTopicEdit: lambda a: f"Topic was editied: {a.title}, and emoji: {a.icon_emoji_id}.",
        types.MessageActionGroupCall: lambda a: f"A group call for {a.duration}.",
        types.MessageActionInviteToGroupCall: lambda a: f"A group call invite with the users: {a.users}",
        types.MessageActionGroupCallScheduled: lambda a: f"A scheduled group call on {a.schedule_date}.",
    }

    text = ""
    if message.text:
        # check for text
        text = f"{message.text}"
    elif isinstance(message, types.MessageService):
        action = message.action
        # Get the action, if it's not something we've written
        # a response for, just give it the default.
        for known_actions, handler in action_handlers.items():
            if isinstance(action, known_actions):
                return handler(action)

        return f"{action} was done."

    return text


"""

These ones are a little more complex than one string of text, 
that's why I'm chsosing to ignore them for now

Todo Actions:

MessageActionChannelMigrateFrom
MessageActionChatMigrateTo
MessageActionConferenceCall
MessageActionSetChatTheme
MessageActionSetChatWallPaper

"""
