import json, asyncio, os, csv, time, argparse
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, ChatAdminRequiredError, ChannelPrivateError
from telethon.tl import types
from dataclasses import dataclass

# Get the API keys
API_ID = os.getenv("TELEGRAM_API_KEY")
API_HASH = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient("Scrapper", API_ID, API_HASH)

# FIXME: Users info may be duplicated
# TODO: Outside dialog reply handler
# TODO: Handle migration
# TODO: Sticker packs handler
# TODO: forwarded from Pic
# TODO: Handle keyboard interrupt
# TODO: stories
# TODO: special emoticon
# TODO: edit date
# TODO: reverse the process (GUI)

@dataclass ()
class Config:
    texts: bool = True
    reactions: bool = True
    dialogInfo: bool = True
    userInfo: bool = True
    files: bool = True
    fileSizeThresholdInBytes: int = (1024 ** 2) * 100

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
        users.add(message.sender_id)

async def fileHanlder(message, messagesRow, fileCounter, FILE_PATH, fileLog, config: Config):
    if not message.file:
        messagesRow.append(0) # File ID
        messagesRow.append(0) # File counter (relative ID)
        messagesRow.append(0) # Big file (flag)
        return 0

    file = getFile(message)

    messagesRow.append(file.id)
    messagesRow.append(fileCounter)
    # if the file is bigger than 100mb, don't download it
    if message.file.size < config.fileSizeThresholdInBytes:
        await downloadFile(message, FILE_PATH, fileCounter)
        messagesRow.append(0)
        return 1
    # keep log of files not downloaded
    fileLog.append(message.id)
    messagesRow.append(1)
    return 0

async def bigFilesHandler(FILE_PATH, fileCounter, dialog):
    fileLog = []
    with open(f"{FILE_PATH}/BigFiles.csv", newline='', encoding="utf-8") as f:
        CSVReader = csv.reader(f)
        fileLog = list(CSVReader)
            
    if len(fileLog) == 0: return
    answer = await asyncio.to_thread(input, f"Do you want to download big files 100mb+? there are {len(fileLog)} of them? (y) ")
    if answer != 'y':
        clearLastLine()
        return
    clearLastLine()

    index = 0
    for messageId in fileLog:
        message = await client.get_messages(dialog, ids=messageId)

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
        CSVBigFilesWriter.writerows(fileLog)

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

async def getReactionList(dialog, message):
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
            reaction.append(react.reaction.emoticon)

            reactions.append(reaction)

        if not request.next_offset:
            break

        offset = request.next_offset

    return reactions

async def reactionHandler(message, CSVReactionsWriter, dialog):
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
    result = await getReactionList(dialog, message)
    CSVReactionsWriter.writerows(result)

def formatETA(seconds):
    seconds = int(seconds)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

def printProgress(totalNumber, currentNumber):
    if totalNumber <= 0:
        print("Progress: N/A")
        return

    progressPercent = min(currentNumber / totalNumber * 100, 100)
    progressInTens  = int (progressPercent // 10)
    progressBar     = ('█' * progressInTens + '░' * (10 - progressInTens))
    print(f"Progress: {progressPercent:3.0f}% {progressBar}...")

def printProgressStatus(totalTimeStart, messageCounter, sizeInMB, totalNumberOfMessages):
    elapsedTime                 = time.perf_counter() - totalTimeStart
    messageRate                 = 0
    downloadRate                = 0
    remainingTime               = 0
    if elapsedTime > 0:
        messageRate             = messageCounter / elapsedTime
        downloadRate            = sizeInMB / elapsedTime
        if messageRate > 0:
            remainingTime       =  (totalNumberOfMessages - messageCounter) / messageRate
    ETA                         = formatETA(remainingTime)

    status = (
        f"Message {messageCounter:^8} | "
        f"{elapsedTime:^8.3f}s | "
        f"{sizeInMB:^8.3f}MB | "
        f"{messageRate:^8.3f}msg/s | "
        f"{downloadRate:^8.3f}MB/s | "
        f"ETA: {ETA:^10}"
    )

    print(status)

async def handleFloodWait(error):
    print(f"You've been rate limited for {error.seconds}s")
    await asyncio.sleep(error.seconds)
    clearLastLine()    

def handleError(dialog, error, messageCounter, fileCounter, PATH, savedDialogInfo):
    if messageCounter and fileCounter and PATH:
        saveCheckpoint(messageCounter, fileCounter, savedDialogInfo, PATH)
    with open("dialogs/erros.txt", 'a') as f:
        f.write(
            f"Error occured in {dialog} "
            f"at message {messageCounter}:\n"
            f"{error}\n\n"
        )

async def archiveGroup(dialog, config: Config):
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
        handleError(dialog.name, e, 0, 0, 0, False)

    bytesToMBRatio           = 1024 ** 2
    sizeInMB                 = 0
    totalTimeStart           = time.perf_counter()
    users                    = set()
    fileLog                  = []
    messageCounter           = 0
    totalNumberOfMessages    = (await client.get_messages(dialog, limit=0)).total
    totalMessagesPercent     = max(totalNumberOfMessages//100, 1)
    fileCounter              = 0
    gotChatInfo              = False
    dialogSavedCheckpoint    = getCheckpoint(PATH)
    if dialogSavedCheckpoint:
        messageCounter       = dialogSavedCheckpoint[0]
        fileCounter          = dialogSavedCheckpoint[1]
        gotChatInfo          = dialogSavedCheckpoint[2]

    printProgress(totalNumberOfMessages, fileCounter)
    printProgressStatus(totalTimeStart, messageCounter, sizeInMB, totalNumberOfMessages)

    try:
        with open(f"{PATH}/TextMessages.csv", 'a') as texts, \
             open(f"{PATH}/Reactions.csv", 'a') as reactions, \
             open(f"{FILE_PATH}/BigFiles.csv", 'w') as fileLogStream:
            CSVMessagesWrtier = csv.writer(texts)
            CSVReactionsWriter = csv.writer(reactions)
            CSVBigFilessWriter = csv.writer(fileLogStream)

            async for message in client.iter_messages(dialog.entity, reverse=True, offset_id=messageCounter):
                # for writing into the file at once
                if config.texts:
                    messagesRow = []
                    messagesRow.append(message.id)

                    await userIdHandler (message, messagesRow, users)
                    
                    await forwardHanlder (message, messagesRow, users)
                    
                    await replyHandler (message, messagesRow)

                    await textHandler (message, messagesRow)

                    messagesRow.append(message.date)
                    CSVMessagesWrtier.writerow(messagesRow)

                if config.files:
                    fileCounter += await fileHanlder (message, messagesRow, fileCounter, FILE_PATH, fileLog, config)
                    if message.file:
                        sizeInMB += message.file.size / bytesToMBRatio

                if config.reactions:
                    await reactionHandler(message, CSVReactionsWriter, dialog)

                messageCounter += 1
                
                if messageCounter % totalMessagesPercent == 0:
                    clearLastLine(2)
                    printProgressStatus(totalTimeStart, messageCounter, sizeInMB, totalNumberOfMessages)
                    printProgress(totalNumberOfMessages, messageCounter)
                    if config.files:
                        emptyFileLog(fileLog, CSVBigFilessWriter, 100)

            if config.dialogInfo and not gotChatInfo:
                await getGroupOrChannelInfo(dialog, PATH, users)

            if config.userInfo:
                await usersHandler(users, PATH)

            saveCheckpoint(messageCounter, fileCounter, True, PATH)

            clearLastLine(3)
            if config.files:
                emptyFileLog(fileLog, CSVBigFilessWriter, 0)
                await bigFilesHandler(FILE_PATH, fileCounter, dialog)
            print(f"Done archiving {dialog.name}!")

    except FloodWaitError as e:
        handleError(dialog.name, e, messageCounter, fileCounter, PATH, False)
        await handleFloodWait(e)
    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        clearLastLine(3)
        print("Please wait a moment while the saving the checkpoint")
        saveCheckpoint(messageCounter, fileCounter, False, PATH)
        clearLastLine()
        print("Done!")
        exit(0)
    except Exception as e:
        handleError(dialog.name, e, messageCounter, fileCounter, PATH, False)

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
    with open(f"{Path}/PhotoInfo.csv", 'w') as f:
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
        handleError(dialog.name, e, 0, 0, 0, False)

async def usersHandler(users, path):
    if not users: return

    with open(f"{path}/Users.csv", 'w') as f:
        CSVWriter = csv.writer(f)
        row = list(users)
        CSVWriter.writerows(row)

    for user in users:
        if isinstance(user, int):
            await getUserInfo(user)

async def getUserInfo(userId):
    user = await client.get_entity(userId)
    filePath = f"dialogs/users/{userId}"

    try:
        os.mkdir(filePath)
    except OSError as e:
        handleError("N/A", e, 0, 0, 0, False)
        return
    except Exception as e:
        handleError("N/A", e, 0, 0, 0, False)
        print(f"Error occurred while trying to archive users:\n{e}")
        return
    
    await getFullRequest(user, filePath)
    await getPhotoInfo(user, filePath)

async def calculateDialogSpace(dialog):
    bytesToMBRatio         = 1024 ** 2
    totalNumberOfMessages  = (await client.get_messages(dialog, limit=0)).total
    totalMessagesPercent   = max(totalNumberOfMessages//100, 1)
    sizeInMB               = 0
    messageCounter         = 0
    totalTimeStart         = time.perf_counter()
    try:
        printProgressStatus(totalTimeStart, messageCounter, sizeInMB, totalNumberOfMessages)
        printProgress(totalNumberOfMessages, messageCounter)

        async for message in client.iter_messages(dialog.entity):
            messageCounter += 1

            if messageCounter % totalMessagesPercent == 0:
                clearLastLine(2)
                printProgressStatus(totalTimeStart, messageCounter, sizeInMB, totalNumberOfMessages)
                printProgress(totalNumberOfMessages, messageCounter)
                
            if message.file: sizeInMB += message.file.size / bytesToMBRatio

        clearLastLine(3)
        print(f"Dialog {dialog.title} will take about {sizeInMB:.3f}MB")

    except FloodWaitError as e:
        handleError(dialog.name, e, 0, 0, 0, False)
        await handleFloodWait(e)

def saveCheckpoint(messageCounter, fileCounter, flagOfGetDialogInfo, dialogPath):
    dialog = {}
    try:
        with open(f"{dialogPath}/CheckPoint.json", 'r') as f:
            dialog = json.load(f) 
            # if any of the inputs is 0 means don't change it, like if you haven't parsed the dialog info yet
            if messageCounter:      dialog[0] = messageCounter
            if fileCounter:         dialog[1] = fileCounter
            if flagOfGetDialogInfo: dialog[2] = flagOfGetDialogInfo
    except (FileNotFoundError, json.JSONDecodeError):
        dialog = [messageCounter, fileCounter, flagOfGetDialogInfo]
        
    with open(f"{dialogPath}/CheckPoint.json", 'w') as f:
        f.write(json.dumps(dialog))

def getCheckpoint(dialogPath):
    try:
        with open(f"{dialogPath}/CheckPoint.json", 'r') as f:
            dialogs = json.load(f)
            return dialogs
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def clearLastLine(numberOfLines = 1):
    # It literally removes the last line in the command prompt
    for _ in range(numberOfLines):
        print("\033[F\033[K", end='')

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--archive-all", action="store_true", help="archive everything")
    parser.add_argument("-t", "--archive-text", action="store_true", help="archive text messages (including forward, reply, edit, and sender_id)")
    parser.add_argument("-r", "--archive-reactions", action="store_true", help="archive message reactions")
    parser.add_argument("-d", "--archive-dialog-info", action="store_true", help="archive dialog info like title, bio, pfps, and etc.")
    parser.add_argument("-u", "--archive-user-info", action="store_true", help="archive info of users in a dialog, like name, bio, pfps, and etc.")
    parser.add_argument("-f", "--archive-file", action="store_true", help="archive files, like photos, videos, documents, and etc. with a size threshold (default: 100MB)")
    parser.add_argument("-b", "--archive-big-files", action="store_true", help="archive all files ignoring the default of 100MB")
    parser.add_argument("-s", "--size-threshold", default=100, type=int, metavar="MB", help="the size threshold for files (default: 100MB)")

    config = Config()

    args = parser.parse_args()

    if args.archive_all:
        config.texts = True
        config.reactions = True
        config.dialogInfo = True
        config.userInfo = True
        config.files = True
        config.fileSizeThresholdInBytes = float('inf')

    else:
        config.texts = args.archive_text
        config.reactions = args.archive_reactions
        config.dialogInfo = args.archive_dialog_info
        config.userInfo = args.archive_user_info
        config.files = args.archive_file
        if args.archive_big_files:
            config.files = True
            config.fileSizeThresholdInBytes = float('inf')
        else:
            config.fileSizeThresholdInBytes = args.size_threshold * (1024 ** 2)

    print("Started...")
    os.makedirs("dialogs", exist_ok=True)
    os.makedirs("dialogs/users", exist_ok=True)

    async for dialog in client.iter_dialogs():
        ans = await asyncio.to_thread(input, f"Do you want to check the approximate size of {dialog.name}? (y) ")
        if (ans == 'y'):
            clearLastLine()
            print(f"Calculating the size of {dialog.name}...")
            await calculateDialogSpace(dialog)
        else:
            clearLastLine()
        ans = await asyncio.to_thread(input, f"Do you want to archive {dialog.name}? (y) ")
        if (ans == 'y'):
            clearLastLine()
            if isinstance(dialog.entity, (types.Chat, types.Channel, types.User)):
                print(f"Archiving {dialog.name}...")
                await archiveGroup(dialog, config)
            else:
                print("Error: can't archive this!")
        else:
            clearLastLine()

with client:
    client.loop.run_until_complete(main())