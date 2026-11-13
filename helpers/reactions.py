import logging
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient, custom, functions, tl, types

from db.models import Reaction

logger = logging.getLogger(__name__)


@dataclass
class ReactionInfo:
    dialog_id: int
    message_id: int
    reactors_id: int
    date: datetime
    reaction: str


async def get_reaction_list(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    message: custom.message.Message,
) -> list[ReactionInfo]:
    """
    A function that extracts reactions from a message.
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

            for react in result or []:
                reactions.append(
                    ReactionInfo(
                        dialog_id=dialog.id,
                        message_id=message.id,
                        reactors_id=get_peer_id(react),
                        date=react.date,
                        reaction=reaction_type(react),
                    )
                )

            if not request or not request.next_offset:
                break

            offset = request.next_offset

        except Exception:
            logger.exception(
                f"Exception occurred while requesting a reaction list at message {message.id}"
            )
            return reactions

    return reactions


def reaction_type(react: types.messages.MessageReactionsList) -> str:
    """
    A function that returns the reaction,
    or its type if it is not a unicode reaction.
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


def get_peer_id(react: types.messages.MessageReactionsList) -> int:
    """
    A function that gets the id of the reactor with
    minimal interaction with the api.
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
    session: AsyncSession, dialog_id: int, message_id: int, react
) -> None:
    """
    A function that interacts with the database to insert reaction data.
    It inserts the reaction data of a reaction in a channel, or where
    you can't see who is reacting.
    """

    new_reaction = Reaction(
        dialog_id=dialog_id,
        message_id=message_id,
        reaction=reaction_type(react),
        count=react.count,
    )

    session.add(new_reaction)


def insert_chat_reaction(
    session: AsyncSession, reaction: ReactionInfo
) -> None:
    """
    A function that interacts with the database to insert reaction data.
    It inserts reaction data of a reaction where the reactor can be seen,
    aka in a group, or a chat, or any other dialog type.
    """

    new_reaction = Reaction(
        dialog_id=reaction.dialog_id,
        message_id=reaction.message_id,
        reactors_id=reaction.reactors_id,
        reacting_date=reaction.date,
        reaction=reaction.reaction,
    )

    session.add(new_reaction)


async def reaction_handler(
    client: TelegramClient,
    dialog: tl.custom.dialog.Dialog,
    message: custom.message.Message,
    session: AsyncSession,
) -> None:
    """
    A function that handles all things having to do with a message
    and its reactions.
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
            insert_chat_reaction(session, react)

    except Exception:
        logger.exception(f"Exception occurred at message {message.id}")
