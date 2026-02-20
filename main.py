import json, asyncio, os, csv, time
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl import types

# Get the API keys
API_ID = os.getenv("TELEGRAM_API_KEY")
API_HASH = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient("Scrapper", API_ID, API_HASH)


async def userIdHandler(message, messagesRow, users):
    # check for the id of the user to add to the message
    if not message.sender: 
        messagesRow.append('0')
        return
    messagesRow.append(str(message.sender.id))
    # check if the sender is not saved
    if message.sender.id not in users:
        users.add(message.sender.id)

# TODO: Keep a separate log of files to download later 
async def fileHanlder(message, messagesRow, fileCounter, FILE_PATH):
    if not message.file:
        messagesRow.append('0')
        messagesRow.append('0')
        messagesRow.append('0')
        return 0
    file = message.file
    # photos don't work with file id in telethon
    if message.photo:
        file = message.photo

    fileName = f"{fileCounter} "
    if message.file.name:
        fileName += message.file.name

    messagesRow.append(str(file.id))
    messagesRow.append(str(fileCounter))
    # if the file is bigger than 100mb, don't download it
    if message.photo or file.size < (1024 ** 2) * 100:
        await message.download_media(file=f"{FILE_PATH}/{fileName}")
        messagesRow.append('0')
    else: 
        # keep log of files not downloaded
        await message.forward_to("me")
        messagesRow.append('1')
    return 1

# TODO: Outside dialog reply handler
# TODO: remove str from these things
async def replyHandler(message, messagesRow):
    # check if this message is a reply to another
    if not message.is_reply:
        messagesRow.append('0')
        return
    reply = await message.get_reply_message()
    if reply:
        messagesRow.append(str(reply.id))
    else:
        messagesRow.append(0)

async def forwardHanlder(message, messagesRow, users):
    forward = message.forward
    if not forward:
        messagesRow.append('0')
        messagesRow.append('0')
        return
    messagesRow.append(f"{forward.from_name}")
    if not forward.from_id:
        messagesRow.append('0')
        return
    entity = forward.from_id
    peerId = None
    if isinstance(entity, types.PeerUser):
        peerId = entity.user_id
    elif isinstance(entity, types.PeerChannel):
        peerId = entity.channel_id
    elif isinstance(entity, types.PeerChat):
        peerId = entity.chat_id
    messagesRow.append(peerId)
    users.add(peerId)
 
async def textHandler(message, messagesRow):
    # check for text
    if message.text:
        messagesRow.append(f"{message.text}")
    elif isinstance(message, types.MessageService):
        action = message.action
        if isinstance(action, types.MessageActionPinMessage):
            messagesRow.append(f"a messaage was pinned")
        elif isinstance(action, types.MessageActionChatAddUser):
            messagesRow.append(f"{action.users} was added")
        elif isinstance(action, types.MessageActionChatJoinedByLink):
            messagesRow.append(f"{action.inviter_id} joined")
        elif isinstance(action, types.MessageActionChatDeleteUser):
            messagesRow.append(f"{action.user_id} was kicked/left")
        elif isinstance(action, types.MessageActionChatEditPhoto):
            messagesRow.append(f"chat photo changed")
        elif isinstance(action, types.MessageActionChatEditTitle):
            messagesRow.append(f"chat title changed to {action.title}")
        elif isinstance(action, types.MessageActionChatCreate):
            messagesRow.append(f"{action.title} was created with users: {action.users}")
        else:
            messagesRow.append(f"{action} was done.")

    else: 
        messagesRow.append("")

# FIXME: something is wrong here
async def reactionHandler(message, CSVReactionsWriter):
    reactions = message.reactions
    if not reactions: return
    reactionsRow = [message.id]

    # For channels
    if not reactions.can_see_list:
        for react in reactions.results or []:
            reactionsRow.append(react.reaction)
            reactionsRow.append(react.count)
        CSVReactionsWriter.writerow(reactionsRow)
        return

    # FIXME: here, to be exact
    # For groups or chats
    for react in reactions.recent_reactions or []:
        reactionsRow.append(react.reaction.emoticon)
        reactionsRow.append(react.date)
        peerId = None
        if isinstance(react.peer_id, types.PeerUser):
            peerId = react.peer_id.user_id
        elif isinstance(react.peer_id, types.PeerChannel):
            peerId = react.peer_id.channel_id
        elif isinstance(react.peer_id, types.PeerChat):
            peerId = react.peer_id.chat_id
        reactionsRow.append(peerId)
    CSVReactionsWriter.writerow(reactionsRow)



# TODO: Topic handler
# TODO: Make the code look better
# TODO: block private groups from being saved
# TODO: Better handle mid-work errors (checkpoints)
async def archiveGroup(dialog, dialogCounter):
    PATH = f"dialogs/groups/dialog {dialogCounter}"
    FILE_PATH = f"{PATH}/file"

    try:
        os.makedirs (f"{PATH}", exist_ok=True)
        os.makedirs (FILE_PATH, exist_ok=True)
        texts = open(f"{PATH}/Text messages.csv", 'a')
        reactions = open(f"{PATH}/Reactions.csv", 'a')
        CSVMessagesWrtier = csv.writer(texts)
        CSVReactionsWriter = csv.writer(reactions)
    except OSError as e:
        print(f"Error making the folders/files: {e}")
        exit()

    users = set()
    fileCounter = 0
    messageCounter = 0
    dialogSavedCheckpoint = getCheckpoint(dialog.id, PATH)
    if dialogSavedCheckpoint:
        messageCounter = dialogSavedCheckpoint[0]
        fileCounter = dialogSavedCheckpoint[1]

    try:
        async for message in client.iter_messages(dialog.entity, reverse=True, offset_id=messageCounter):
            # for writing into the file at once
            messagesRow = []
            messagesRow.append(str(message.id))
            
            await userIdHandler (message, messagesRow, users)

            fileCounter += await fileHanlder (message, messagesRow, fileCounter, FILE_PATH)
            
            await replyHandler (message, messagesRow)

            await forwardHanlder (message, messagesRow, users)
            
            await textHandler (message, messagesRow)
            
            await reactionHandler(message, CSVReactionsWriter)

            messagesRow.append(str(message.date))
            CSVMessagesWrtier.writerow(messagesRow)
            messageCounter += 1

        texts.close()
        saveCheckpoint(dialog.id, messageCounter, fileCounter, False, PATH)

    except FloodWaitError as e:
        print(f"You've been rate limited for {e.seconds}s")
        asyncio.sleep(e.seconds)
        saveCheckpoint(dialog.id, messageCounter, fileCounter, False, PATH)
    except Exception as e:
        print(f"An error {e} occurred at message {messageCounter}")
        saveCheckpoint(dialog.id, messageCounter, fileCounter, False, PATH)

async def getGroupOrChannelInfo(dialog, PATH, users):
    if dialog.is_user: return
    infoPath = f"{PATH}/Dialog Info"
    os.makedirs(infoPath, exist_ok=True)
    with open(f"{infoPath}/info.csv") as f:
        infoRow = []
        infoRow.append(str(dialog.id))
        infoRow.append(f"{dialog.name}")
        if dialog.username:
            infoRow.append(dialog.username)
        else:
            infoRow.append(dialog.access_hash)

        infoRow.append(dialog.participants_count)

        CSVInfoWriter = csv.writer(f)
        CSVInfoWriter.writerow(infoRow)
        
    async for photo in client.iter_profile_photos():
        await client.download_file(photo, file=f"{infoPath}/{photo.date} : {photo.name}")

    if not dialog.is_group: return

    if not dialog.participants_hidden:
        for user in dialog.users:
            if user.id not in users:
                users.add(user.id)
    for user in users:
        await getGroupOrChannelInfo(user, PATH, users)

# TODO: async def getUserInfo(userId):
# TODO: Archive channel

async def calculateDialogSpace(dialog):
    sizeInMB = 0
    messageCounter = 0
    mult = 0
    totalTimeStart = time.perf_counter()
    try:
        async for message in client.iter_messages(dialog.entity):
            messageCounter += 1

            if messageCounter >= 10_000:
                messageCounter = 0
                mult += 1
                print(f"Message {mult * 10_000}, current time {time.perf_counter() - totalTimeStart:.3f}s the current space: {sizeInMB:.3f}MB")

            if not message.file: pass
            else: sizeInMB += message.file.size/(1024 ** 2)

        print(f"Dialog {dialog.title} will take about {sizeInMB:.3f}MB")

    except FloodWaitError as e:
        print(f"You've been rate limited for {e.seconds}s")
        await asyncio.sleep(e.seconds)

    print(f"It had taken {time.perf_counter() - totalTimeStart:.3f}s")
    print(f"Total size of the chat: {sizeInMB:.3f}mb")

# TODO: maybe make this a class that waits for all inputs to be fulfilled or something, idk
def saveCheckpoint(dialogId, messageCounter, fileCounter, flagOfGetDialogInfo, dialogPath):
    dialog = {}
    try:
        with open(f"{dialogPath}/state.json", 'r') as f:
            dialog = json.load(f) 
            # if any of the inputs is 0 means don't change it, like if you haven't parsed the dialog info yet
            if messageCounter: dialog[0] = messageCounter
            if fileCounter: dialog[1] = fileCounter
            if flagOfGetDialogInfo: dialog[2] = flagOfGetDialogInfo
    except (FileNotFoundError, json.JSONDecodeError):
        dialog = [messageCounter, fileCounter, flagOfGetDialogInfo]
        
    with open(f"{dialogPath}/state.json", 'w') as f:
        f.write(json.dumps(dialog))

def getCheckpoint(dialogId, dialogPath):
    try:
        with open(f"{dialogPath}/state.json", 'r') as f:
            dialogs = json.load(f)
            return dialogs
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    

async def main():
    print("Started...")
    os.makedirs("dialogs", exist_ok=True)
    dialogCounter = 1

    async for dialog in client.iter_dialogs():        
        if (input(f"Do you want to check the approximate size of {dialog.name}? (y) ") == 'y'):
            await calculateDialogSpace(dialog)

        if (input(f"Do you want to archive {dialog.name}? (y) ") == 'y'):
            if dialog.is_group:
                await archiveGroup(dialog, dialogCounter)
            dialogCounter += 1

with client:
    client.loop.run_until_complete(main())
