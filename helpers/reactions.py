import logging
from datetime import datetime

from sqlalchemy.orm import Session
from telethon import TelegramClient, custom, functions, tl, types

from db.models import Reaction

logger = logging.getLogger(__name__)


async def get_reaction_list(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    message: custom.message.Message,
) -> list[tuple[int, int, int, datetime, str]]:
    """
    A function that extracts reactions from a message.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

    Returns:
        List[Tuple(
            int (dialog id),
            int (message id),
            int (reactor's id),
            datetime (date of reacting),
            str (reaction),
        )]
    """

    id = message.id
    offset = None
    reactions = []
    while True:
        try:
            request = await client(
                functions.messages.GetMessageReactionsListRequest(
                    peer=dialog,
                    id=id,
                    reaction=None,
                    limit=10000,
                    offset=offset,
                )
            )
            result = request.reactions
        except Exception:
            logger.exception(
                f"Exception occurred while requesting a reaction list at message {message.id}"
            )

        for react in result or []:
            reactions.append(
                (
                    dialog.id,
                    message.id,
                    get_peer_id(react),
                    react.date,
                    reaction_type(react),
                )
            )

        if not request or not request.next_offset:
            break

        offset = request.next_offset

    return reactions


def reaction_type(react) -> str:
    """
    A function that returns the reaction,
    or its type if it is not a unicode reaction.

    Args:
        react:
            The returned value of telethon's get reaction functions.

    Returns:
        str:
            The reaction, or its type if it is not a unicode reaction.
    """

    # For safety
    if not react:
        return "No Emoji"

    # If it is a typical unicode reaction
    if isinstance(react.reaction, types.ReactionEmoji):
        return react.reaction.emoticon

    # Else if it a custom reaction.
    # For now to avoid errors we'll skip it
    elif isinstance(react.reaction, types.ReactionCustomEmoji):
        return "Custom Emoji"

    else:
        logger.warning(f"Unknown reaction type: {react.reaction}")
        return "Unknown Emoji Type"


def get_peer_id(react) -> int:
    """
    A function that gets the id of the reactor with
    minimal interaction with the api.

    Args:
        react:
            The returned value of telethon's get reaction functions.

    Returns:
        int:
            The id of the entity that made the reaction.
    """

    # For safety
    if not react:
        return 0

    if isinstance(react.peer_id, types.PeerUser):
        return react.peer_id.user_id

    elif isinstance(react.peer_id, types.PeerChannel):
        return react.peer_id.channel_id

    elif isinstance(react.peer_id, types.PeerChat):
        return react.peer_id.chat_id

    else:
        logger.warning(f"Unknown entity reacted: {react.peer_id}")
        return 0


def insert_channel_reaction(
    session: Session, dialog_id: int, message_id: int, react
) -> None:
    """
    A function that interacts with the database to insert reaction data.
    It inserts the reaction data of a reaction in a channel, or where
    you can't see who is reacting.

    Args:
        session (sqlalchemy.Session):
            The session of the database.

        dialog_id (int):
            The id of the dialog where the message is reacted on.

        message_id (int):
            The id of the message reacted on.

        react:
            The returned value of telethon's get reaction functions.
    """

    new_reaction = Reaction(dialog_id=dialog_id, message_id=message_id, reaction=reaction_type(react), count=react.count)

    session.add(new_reaction)


def insert_chat_reaction(
    session: Session, result: tuple[int, int, int, datetime, str]
) -> None:
    """
    A function that interacts with the database to insert reaction data.
    It inserts reaction data of a reaction where the reactor can be seen,
    aka in a group, or a chat, or any other dialog type.

    Args:
        session (sqlalchemt.Session):
            The session of the database.

        result:
            The reaction's data: tuple(
                int (dialog id),
                int (message id),
                int (reactor's id),
                datetime (date of reacting),
                str (reaction),
            )
    """

    new_reaction = Reaction(
        dialog_id=result[0],
        message_id=result[1],
        reactors_id=result[2],
        reacting_date=result[3],
        reaction=result[4],
    )

    session.add(new_reaction)


async def reaction_handler(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    message: custom.message.Message,
    session: Session,
) -> None:
    """
    A function that handles all things having to do with a message
    and its reactions.

    Args:
        client (telethon.TelegramClient):
            Your account's client.

        dialog (telethon.tl.custom.dialog.Dialog):
            The object which you get from client.iter_dialogs.

        message (telethon.custom.message.Message):
            A telegram dialog's message provided by telethon.

        session (sqlalchemy.Session):
            The session of the database.
    """

    try:
        # For safety
        if not message or not message.reactions:
            return

        reactions = message.reactions

        # For channels
        if not reactions.can_see_list:
            for react in reactions.results or []:
                insert_channel_reaction(session, dialog.id, message.id, react)

            return

        # For groups or chats
        result = await get_reaction_list(client, dialog, message)

        for react in result:
            if len(react) != 0:
                insert_chat_reaction(session, react)

    except Exception:
        logger.exception(f"Exception occurred at message {message.id}")
