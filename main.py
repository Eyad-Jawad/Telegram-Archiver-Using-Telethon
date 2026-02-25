import json, asyncio, os, csv, time
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, ChatAdminRequiredError, ChannelPrivateError
from telethon.tl import types

# Get the API keys
API_ID = os.getenv("TELEGRAM_API_KEY")
API_HASH = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient("Scrapper", API_ID, API_HASH)

# FIXME: something is wrong with the reaction handler
# FIXME: Users info may be duplicated
# TODO: Make a config class
# TODO: Outside dialog reply handler
# TODO: Handle migration
# TODO: Add a time estimator
# TODO: Sticker packs handler
# TODO: asyncio.to_thread


async def userIdHandler(message, messagesRow, users):
    # check for the id of the user to add to the message
    if message.post_author:
        messagesRow.append(message.post_author)
    elif not message.sender_id: 
        messagesRow.append(0)
        return
    messagesRow.append(message.sender_id)
    # check if the sender is not saved
    if message.sender_id not in users:
        users.add(message.sender.id)

async def fileHanlder(message, messagesRow, fileCounter, FILE_PATH, fileLog):
    if not message.file:
        messagesRow.append(0) # File ID
        messagesRow.append(0) # File counter (relative ID)
        messagesRow.append(0) # Big file (flag)
        return 0

    file = getFile(message)

    messagesRow.append(file.id)
    messagesRow.append(fileCounter)
    # if the file is bigger than 100mb, don't download it
    if message.photo or file.size < (1024 ** 2) * 100:
        await downloadFile(message, FILE_PATH, fileCounter)
        messagesRow.append(0)
    else: 
        # keep log of files not downloaded
        fileLog.append(message.id)
        messagesRow.append(1)
    return 1

async def bigFilesHandler(FILE_PATH, fileCounter, dialog):
    fileLog = []
    with open(f"{FILE_PATH}/BigFiles.csv", newline='', encoding="utf-8") as f:
        CSVReader = csv.reader(f)
        fileLog = list(CSVReader)
            
    if len(fileLog) == 0: return
    answer = input(f"Do you want to download big files 100mb+? there are {len(fileLog)} of them? (y) ")
    if answer != 'y':
        clearLastLine()
        return
    clearLastLine()

    index = 0
    for fileID in fileLog:
        message = await client.get_messages(dialog, ids=fileID)

        print(f"{index}/{len(fileLog)} : {message.file.size / (1024 ** 2):.2f}MB", end='\r')

        await downloadFile(message, FILE_PATH, fileCounter)
        fileCounter += 1
        index += 1

async def downloadFile(message, FILE_PATH, fileCounter):
    file = getFile(message)
    fileName = f"{fileCounter} "

    if message.photo:
        fileName += ".jpg"
    elif file.name:
        fileName += file.name 

    await message.download_media(file=f"{FILE_PATH}/{fileName}")

def getFile(message):
    file = message.file
    # photos don't work with file id in telethon
    if message.photo:
        file = message.photo
    return file

def emptyFileLog(fileLog, CSVBigFilesWriter, threshold):
    if len(fileLog) >= threshold:
        CSVBigFilesWriter.write_rows(fileLog)

async def replyHandler(message, messagesRow):
    # check if this message is a reply to another
    if not message.is_reply:
        messagesRow.append(0)
        return
    reply = await message.get_reply_message()
    if reply:
        messagesRow.append(reply.id)
    else:
        messagesRow.append(0)

async def forwardHanlder(message, messagesRow, users):
    forward = message.forward
    if not forward:
        messagesRow.append(0)
        messagesRow.append(0)
        return
    messagesRow.append(f"{forward.from_name}")
    if not forward.from_id:
        messagesRow.append(0)
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

def printProgress(totalNumber, currentNumber):
    whiteBlock              = '█'
    greyBlock               = '░'
    progressPercent         = currentNumber / totalNumber * 100
    progressInTens          = int (progressPercent // 10)
    progressBar             = (whiteBlock * progressInTens + greyBlock * (10 - progressInTens))
    print(f"Progress: {progressPercent:3.0f}% {progressBar}...")

def printProgressStatus(totalTimeStart, messageCounter, sizeInMB):
    elapsedTime = time.perf_counter() - totalTimeStart

    status = (
        f"Message {messageCounter:8} | "
        f"{elapsedTime:8.3f}s | "
        f"{sizeInMB:8.3f}MB"
    )

    print(status)

async def archiveGroup(dialog):
    PATH = f"dialogs"

    if isinstance(dialog.entity, types.User):
        PATH += f"/users/{dialog.id}"
    elif isinstance(dialog.entity, types.Chat):
        PATH += f"/chats/{dialog.id}"
    else:
        PATH += f"/groups/{dialog.id}"

    FILE_PATH = f"{PATH}/files"

    try:
        os.makedirs (f"{PATH}", exist_ok=True)
        os.makedirs (FILE_PATH, exist_ok=True)
    except OSError as e:
        print(f"Error making the folders/files: {e}")
        exit()

    users                               = set()
    fileLog                             = []
    messageCounter                      = 0
    totalNumberOfMessagegs              = (await client.get_messages(dialog, limit=0)).total
    hunderedOfTotalNumberOfMessagegs    = max(totalNumberOfMessagegs//100, 1)
    fileCounter                         = 0
    gotChatInfo                         = False
    dialogSavedCheckpoint               = getCheckpoint(PATH)
    if dialogSavedCheckpoint:
        messageCounter                  = dialogSavedCheckpoint[0]
        fileCounter                     = dialogSavedCheckpoint[1]
        gotChatInfo                     = dialogSavedCheckpoint[2]

    printProgress(totalNumberOfMessagegs, fileCounter)

    try:
        with open(f"{PATH}/Text messages.csv", 'a') as texts, \
             open(f"{PATH}/Reactions.csv", 'a') as reactions, \
             open(f"{FILE_PATH}/BigFiles.csv", 'w') as fileLogStream:
            CSVMessagesWrtier = csv.writer(texts)
            CSVReactionsWriter = csv.writer(reactions)
            CSVBigFilessWriter = csv.writer(fileLogStream)

            async for message in client.iter_messages(dialog.entity, reverse=True, offset_id=messageCounter):
                # for writing into the file at once
                messagesRow = []
                messagesRow.append(message.id)
                
                await userIdHandler (message, messagesRow, users)

                fileCounter += await fileHanlder (message, messagesRow, fileCounter, FILE_PATH, fileLog)
                
                await replyHandler (message, messagesRow)

                await forwardHanlder (message, messagesRow, users)
                
                await textHandler (message, messagesRow)
                
                await reactionHandler(message, CSVReactionsWriter)

                messagesRow.append(message.date)
                CSVMessagesWrtier.writerow(messagesRow)
                messageCounter += 1

                if messageCounter % hunderedOfTotalNumberOfMessagegs == 0:
                    clearLastLine()
                    printProgress(totalNumberOfMessagegs, messageCounter)
                emptyFileLog(fileLog, CSVBigFilessWriter, 100)

            if not gotChatInfo:
                await getGroupOrChannelInfo(dialog, PATH, users)

            await usersHandler(users, PATH)
            saveCheckpoint(messageCounter, fileCounter, True, PATH)

            clearLastLine(2)

            emptyFileLog(fileLog, CSVBigFilessWriter, 0)
            await bigFilesHandler(fileLog, FILE_PATH, fileCounter, dialog)

    except FloodWaitError as e:
        print(f"You've been rate limited for {e.seconds}s")
        await asyncio.sleep(e.seconds)
        saveCheckpoint(messageCounter, fileCounter, False, PATH)
    except Exception as e:
        print(f"An error {e} occurred at message {messageCounter}")
        saveCheckpoint(messageCounter, fileCounter, False, PATH)

async def getGroupOrChannelInfo(dialog, PATH, users):
    dialog = dialog.entity    
    infoPath = f"{PATH}/Dialog Info"
    os.makedirs(infoPath, exist_ok=True)

    await getFullRequest(dialog, infoPath)

    await getPhotoInfo(dialog, infoPath)

    await addUsersToSet(dialog, users)

async def getFullRequest(dialog, Path):
    with open(f"{Path}/info.txt", 'w') as f:
        fullRequest = None

        if isinstance(dialog, types.Channel):
            fullRequest = await client(functions.channels.GetFullChannelRequest(dialog))
        elif isinstance(dialog, types.User):
            fullRequest = await client(functions.users.GetFullUserRequest(dialog))
        else:
            fullRequest = await client(functions.messages.GetFullChatRequest(dialog))
        f.write(fullRequest.stringify())

async def getPhotoInfo(dialog, Path):
    with open(f"{Path}/photosInfo.csv", 'w') as f:
        CSVInfoWriter = csv.writer(f)
        photoDataRow = []

        async for photo in client.iter_profile_photos(dialog):
            await client.download_media(photo, file=Path)
            photoDataRow.append(photo.date)
        CSVInfoWriter.writerow(photoDataRow)

async def addUsersToSet(dialog, users):
    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)
    except (ChatAdminRequiredError, ChannelPrivateError, Exception) as e:
        return users.add(f"Exception: {e}")

async def usersHandler(users, path):
    with open(f"{path}/users.csv", 'w') as f:
        CSVWriter = csv.writer(f)
        row = list(users)
        CSVWriter.writerow(row)

    if not users: return
    for user in users:
        if isinstance(user, int):
            await getUserInfo(user)

async def getUserInfo(userId):
    user = await client.get_entity(userId)
    filePath = f"dialogs/users/{userId}"

    try:
        os.mkdir(filePath)
    except OSError:
        return
    except Exception as e:
        print(f"Error occurred while trying to archive users:\n{e}")
        return
    
    await getFullRequest(user, filePath)
    await getPhotoInfo(user, filePath)

async def calculateDialogSpace(dialog):
    totalNumberOfMessagegs              = (await client.get_messages(dialog, limit=0)).total
    hunderedOfTotalNumberOfMessagegs    = max(totalNumberOfMessagegs//100, 1)
    sizeInMB                            = 0
    messageCounter                      = 0
    totalTimeStart                      = time.perf_counter()
    try:
        printProgressStatus(totalTimeStart, messageCounter, sizeInMB)
        printProgress(totalNumberOfMessagegs, messageCounter)
        async for message in client.iter_messages(dialog.entity):
            messageCounter += 1

            if messageCounter % hunderedOfTotalNumberOfMessagegs == 0:
                clearLastLine(2)
                printProgressStatus(totalTimeStart, messageCounter, sizeInMB)
                printProgress(totalNumberOfMessagegs, messageCounter)
            if not message.file: pass
            else: sizeInMB += message.file.size/(1024 ** 2)

        print(f"Dialog {dialog.title} will take about {sizeInMB:.3f}MB")

    except FloodWaitError as e:
        print(f"You've been rate limited for {e.seconds}s")
        await asyncio.sleep(e.seconds)
        clearLastLine()

    clearLastLine(2)
    print(f"It had taken {time.perf_counter() - totalTimeStart:.3f}s")
    print(f"Total size of the chat: {sizeInMB:.3f}mb")

def saveCheckpoint(messageCounter, fileCounter, flagOfGetDialogInfo, dialogPath):
    dialog = {}
    try:
        with open(f"{dialogPath}/state.json", 'r') as f:
            dialog = json.load(f) 
            # if any of the inputs is 0 means don't change it, like if you haven't parsed the dialog info yet
            if messageCounter:      dialog[0] = messageCounter
            if fileCounter:         dialog[1] = fileCounter
            if flagOfGetDialogInfo: dialog[2] = flagOfGetDialogInfo
    except (FileNotFoundError, json.JSONDecodeError):
        dialog = [messageCounter, fileCounter, flagOfGetDialogInfo]
        
    with open(f"{dialogPath}/state.json", 'w') as f:
        f.write(json.dumps(dialog))

def getCheckpoint(dialogPath):
    try:
        with open(f"{dialogPath}/state.json", 'r') as f:
            dialogs = json.load(f)
            return dialogs
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def clearLastLine(numberOfLines = 1):
    # It literally removes the last line in the command prompt
    for _ in range(numberOfLines):
        print("\033[F\033[K", end="")

async def main():
    print("Started...")
    os.makedirs("dialogs", exist_ok=True)
    os.makedirs("dialogs/users", exist_ok=True)

    async for dialog in client.iter_dialogs():        
        if (input(f"Do you want to check the approximate size of {dialog.name}? (y) ") == 'y'):
            await calculateDialogSpace(dialog)
        
        clearLastLine()

        if (input(f"Do you want to archive {dialog.name}? (y) ") == 'y'):
            if isinstance(dialog.entity, (types.Chat, types.Channel, types.User)):
                await archiveGroup(dialog)
            else:
                print("Error: can't archive this!")

        clearLastLine()

with client:
    client.loop.run_until_complete(main())