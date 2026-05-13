from telethon import functions, types, custom

async def getReactionList(client, dialog, message: custom.message.Message) -> list:
    id = message.id
    offset = None
    reactions = []
    while True:
        request = await client (
            functions.messages.GetMessageReactionsListRequest(
                peer=dialog,
                id=id,
                reaction=None,
                limit=100,
                offset=offset
            )
        )
        result = request.reactions

        for react in result:
            reaction = [message.id]        
            peerId = None

            if isinstance(react.peer_id, types.PeerUser):
                peerId = react.peer_id.user_id

            elif isinstance(react.peer_id, types.PeerChannel):
                peerId = react.peer_id.channel_id

            elif isinstance(react.peer_id, types.PeerChat):
                peerId = react.peer_id.chat_id

            reaction.append(peerId)
            reaction.append(react.date)

            # for now to avoid errors we'll skip it
            if isinstance(react.reaction, types.ReactionEmoji):
                reaction.append(react.reaction.emoticon)
            elif isinstance(react.reaction, types.ReactionCustomEmoji):
                reaction.append("Custom emoji")
            else:
                reaction.append("Unkown reaction type")

            reactions.append(reaction)

        if not request.next_offset:
            break

        offset = request.next_offset

    return reactions

async def reactionHandler(client, dialog, message: custom.message.Message, CSVReactionsWriter) -> None:
    reactions = message.reactions
    if not reactions: return
    result = []
    # For channels
    if not reactions.can_see_list:
        for react in reactions.results or []:
            reactionsRow = [
                message.id,
                react.reaction,
                react.count
            ]

            result.append(reactionsRow)

        CSVReactionsWriter.writerows(result)
        return

    # For groups or chats
    result = await getReactionList(client, dialog, message)
    CSVReactionsWriter.writerows(result)