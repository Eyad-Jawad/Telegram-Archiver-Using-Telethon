from telethon import functions, types, custom
import sqlite3, logging

logger = logging.getLogger(__name__)


async def getReactionList(
    client, dialog, message: custom.message.Message
) -> list[list[str | int]]:
    id = message.id
    offset = None
    reactions = []
    while True:
        try:
            request = await client(
                functions.messages.GetMessageReactionsListRequest(
                    peer=dialog, id=id, reaction=None, limit=100, offset=offset
                )
            )
            result = request.reactions
        except Exception as e:
            logger.exception(
                f"Exception occurred while requesting a reaction list : {e}"
            )

        for react in result or []:
            reactions.append(
                [
                    dialog.id,
                    message.id,
                    getPeerId(react),
                    react.date,
                    reactionType(react),
                ]
            )

        if not request or not request.next_offset:
            break

        offset = request.next_offset

    return reactions


def reactionType(react) -> str:
    if not react:
        return "No Emoji"

    if isinstance(react.reaction, types.ReactionEmoji):
        return react.reaction.emoticon

    # for now to avoid errors we'll skip it
    elif isinstance(react.reaction, types.ReactionCustomEmoji):
        return "Custom Emoji"

    else:
        return "Unknown Emoji Type"


def getPeerId(react) -> int:
    if not react:
        return 0

    if isinstance(react.peer_id, types.PeerUser):
        return react.peer_id.user_id

    elif isinstance(react.peer_id, types.PeerChannel):
        return react.peer_id.channel_id

    elif isinstance(react.peer_id, types.PeerChat):
        return react.peer_id.chat_id

    else:
        return 0


def insertChannelReaction(
    cursor: sqlite3.Cursor, dialogId: int, messageId: int, react
) -> None:
    cursor.execute(
        "INSERT INTO reactions (dialogId, messageId, reaction, count) VALUES (?, ?, ?, ?)",
        [dialogId, messageId, reactionType(react), react.count],
    )


def insertChatReaction(cursor: sqlite3.Cursor, result: list[str | int]) -> None:
    cursor.execute(
        "INSERT INTO reactions (dialogId, messageId, reactorsId, dateOfReacting, reaction) VALUES (?, ?, ?, ?, ?)",
        result,
    )


async def reactionHandler(
    client, dialog, message: custom.message.Message, cursor: sqlite3.Cursor
) -> None:
    try:
        if not message or not message.reactions:
            return

        reactions = message.reactions

        # For channels
        if not reactions.can_see_list:
            for react in reactions.results or []:
                insertChannelReaction(cursor, dialog.id, message.id, react)

            return

        # For groups or chats
        result = await getReactionList(client, dialog, message)

        for react in result:
            if len(react) != 0:
                insertChatReaction(cursor, react)

    except Exception as e:
        logger.exception(f"Excepetion occurred : {e}")
