import logging

from telethon import custom, types
from telethon.utils import get_peer_id

from db.models import Message

logger = logging.getLogger(__name__)


def reply_handler(
    tel_msg: custom.message.Message, db_msg: Message, users: set[int]
) -> None:
    """
    A function that handles message replies. It has many edge cases:
    reply to user, reply to private chat, reply to channel, and perhaps more.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        db_msg (db.models.Message):
            The database orm object that holds the data and will
            be appended into the database.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.
    """

    # check if this message is a reply to another
    try:
        # for safety
        if not tel_msg or not tel_msg.reply_to:
            return

        # check if it's from a user or a channel
        replied_to = tel_msg.reply_to

        # What to do with a reply to a story
        # temp solution unitl I make some stuff for stories
        if isinstance(replied_to, types.MessageReplyStoryHeader):
            db_msg.replied_to_text = "Replied to a story"
            return

        if not (replied_to and replied_to.reply_to_peer_id):
            # This case is for replies from private dialogs
            if not tel_msg.reply_to_msg_id:
                db_msg.replied_to_text = f"{tel_msg.reply_to.reply_from.from_name}:{tel_msg.reply_to.quote_text}"
                return

            db_msg.replied_to_id = tel_msg.reply_to_msg_id
            db_msg.replied_to_text = tel_msg.reply_to.quote_text
            return

        # if it's from a channel
        replied_to_id = get_peer_id(replied_to.reply_to_peer_id)

        if replied_to_id not in users:
            users.add(replied_to_id)

        db_msg.replied_to_id = tel_msg.reply_to_msg_id
        db_msg.replied_to_entity_id = replied_to_id
        db_msg.replied_to_text = tel_msg.reply_to.quote_text

        return

    except Exception:
        logger.exception(f"Exception occurred at message {tel_msg}")
        return


def forward_handler(
    tel_msg: custom.message.Message, db_msg: Message, users: set[int]
) -> None:
    """
    A function that handles forwarded messages from users with
    hidden or shown profiles, and from other enitities like channels.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        db_msg (db.models.Message):
            The database orm object that holds the data and will
            be appended into the database.

        users (set[int]):
            A set of user ids or any kind of entity where
            entity ids accumulate over the time archiving.
    """

    try:
        # For safety.
        if not tel_msg or not tel_msg.forward:
            return

        forward = tel_msg.forward
        db_msg.forward_from_username = forward.from_name

        # Users who have their profile hidden, or
        # private channels have their id also hidden.
        if not forward.from_id:
            return

        entity = forward.from_id
        peer_id = get_peer_id(entity)

        if peer_id not in users:
            users.add(peer_id)

        db_msg.forward_from_user_id = peer_id
        return

    except Exception:
        logger.exception(f"Exception occurred at message {tel_msg.id}")
        return


def text_handler(tel_msg: custom.message.Message, db_msg) -> None:
    """
    A function that handles text messages, as well as actions
    if the message happens not to be a text message.

    Args:
        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        db_msg (db.models.Message):
            The database orm object that holds the data and will
            be appended into the database.
    """

    action_handlers = {
        types.MessageActionPinMessage: lambda a: "A message was pinned.",
        types.MessageActionChatAddUser: lambda a: f"{a.users} was added.",
        types.MessageActionChatJoinedByLink: lambda a: (
            f"{a.inviter_id} joined."
        ),
        types.MessageActionChatJoinedByRequest: lambda a: (
            "A user joined by request."
        ),
        types.MessageActionChatDeleteUser: lambda a: (
            f"{a.user_id} was kicked/left."
        ),
        types.MessageActionChatEditPhoto: lambda a: "Chat photo was changed.",
        types.MessageActionChatDeletePhoto: lambda a: "Chat photo was deleted.",
        types.MessageActionChatEditTitle: lambda a: (
            f"Chat title was changed to {a.title}."
        ),
        types.MessageActionChatCreate: lambda a: (
            f"{a.title} was created with users: {a.users}."
        ),
        types.MessageActionChannelCreate: lambda a: f"{a.title} was created.",
        types.MessageActionHistoryClear: lambda a: (
            "Message history was cleared."
        ),
        types.MessageActionPhoneCall: lambda a: (
            f"A {'video' if a.video else ''} call for {a.duration}."
        ),
        types.MessageActionTopicEdit: lambda a: (
            f"Topic was editied: {a.title}, and emoji: {a.icon_emoji_id}."
        ),
        types.MessageActionGroupCall: lambda a: (
            f"A group call for {a.duration}."
        ),
        types.MessageActionInviteToGroupCall: lambda a: (
            f"A group call invite with the users: {a.users}"
        ),
        types.MessageActionGroupCallScheduled: lambda a: (
            f"A scheduled group call on {a.schedule_date}."
        ),
    }

    text = ""
    if tel_msg.text:
        # check for text
        text = f"{tel_msg.text}"
    elif isinstance(tel_msg, types.MessageService):
        action = tel_msg.action
        # Get the action, if it's not something we've written
        # a response for, just give it the default.
        for known_actions, handler in action_handlers.items():
            if isinstance(action, known_actions):
                db_msg.text = handler(action)
                return

        db_msg.text = f"{action} was done."
        return

    db_msg.text = text
    return


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
