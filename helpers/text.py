from telethon import types, utils, custom

async def replyHandler(message: custom.message.Message, messagesRow: list, users: set[int]) -> None:
    # check if this message is a reply to another
    if not message.reply_to:
        messagesRow[4] = 0
        return
    messagesRow[4] = message.reply_to_msg_id

    replyedTo = message.reply_to
    if not (replyedTo and replyedTo.reply_to_peer_id): 
        return
    
    replyedToID = utils.get_peer_id(replyedTo.reply_to_peer_id)
    if replyedToID not in users:
        messagesRow[4] = f"{replyedToID}:{message.reply_to_msg_id}"
        users.add(replyedToID)

async def forwardHandler(message: custom.message.Message, messagesRow: list, users: set[int]) -> None:
    forward = message.forward
    if not forward:
        messagesRow[2] = 0
        messagesRow[3] = 0
        return
    messagesRow[2] = f"{forward.from_name}"
    if not forward.from_id:
        messagesRow[3] = 0
        return
    entity = forward.from_id
    peerId = utils.get_peer_id(entity)
    messagesRow[3] = peerId
    if peerId not in users:
        users.add(peerId)
 
async def textHandler(message: custom.message.Message, messagesRow: list, users: set) -> None:
    # check for text
    text = ""
    if message.text:
        text = (f"{message.text}")
    elif isinstance(message, types.MessageService):
        action = message.action
        if isinstance(action, types.MessageActionPinMessage):
            text = (f"a message was pinned")
        elif isinstance(action, types.MessageActionChatAddUser):
            text = (f"{action.users} was added")
        elif isinstance(action, types.MessageActionChatJoinedByLink):
            text = (f"{action.inviter_id} joined")
        elif isinstance(action, types.MessageActionChatDeleteUser):
            text = (f"{action.user_id} was kicked/left")
        elif isinstance(action, types.MessageActionChatEditPhoto):
            text = (f"chat photo changed")
        elif isinstance(action, types.MessageActionChatEditTitle):
            text = (f"chat title changed to {action.title}")
        elif isinstance(action, types.MessageActionChatCreate):
            text = (f"{action.title} was created with users: {action.users}")
        else:
            text = (f"{action} was done.")

    messagesRow[5] = text
