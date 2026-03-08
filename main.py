import json, asyncio, os, csv, time, argparse
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, ChatAdminRequiredError, ChannelPrivateError
from telethon.tl import types, custom
from dataclasses import dataclass

# Get the API keys
API_ID = os.getenv("TELEGRAM_API_KEY")
API_HASH = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient("Scrapper", API_ID, API_HASH)

# TODO: change message row so it has fixed length

# FIXME: Users info may be duplicated
# FIXME: Memory issues for some data types (iterators): (write into a file perhaps)
# FIXME: When getting a floodwait a message will be skipped
# FIXME: When replying to a message from a private chat the method fails:'TotalList' object has no attribute 'id'
# TODO: Outside dialog reply handler
# TODO: Handle migration
# TODO: Sticker packs handler
# TODO: forwarded from Pic
# TODO: stories
# TODO: special emoticon
# TODO: edit date
# TODO: reverse the process (GUI)
# TODO: add the method of only extracting one's messages 
# TODO: On channel get views

@dataclass ()
class Config:
    checkSize: bool = False
    texts: bool = True
    reactions: bool = True
    dialogInfo: bool = True
    userInfo: bool = True
    files: bool = True
    fileSizeThresholdInBytes: int = (1024 ** 2) * 100

class File:
    def __init__(self, path:str, sizeThreshold: int) -> None:
        self.sizeThreshold: int       = sizeThreshold # in bytes
        self.counter:       int       = 1
        self.path:          str       = path + "/files"
        self.skippedStack:  list[int] = []

    async def handle(self, message: custom.message.Message, messagesRow: list) -> None:
        file = message.file
        if not file:
            messagesRow.append(0) # File ID
            messagesRow.append(0) # File counter (relative ID)
            messagesRow.append(0) # Big file (flag)
            return

        if message.photo:
            messagesRow.append(message.photo.id)
        else:
            messagesRow.append(file.id)

        if file.size < self.sizeThreshold:
            messagesRow.append(0)
            await self.downloadFiles(message)
            return

        # keep log of files not downloaded
        messagesRow.append(1)

        self.skippedStack.append(message.id)
        if len(self.skippedStack) >= 100:
            self.emptyBigFilesLog()

        return
    
    async def downloadFiles(self, message: custom.message.Message) -> None:
        file = message.file

        fileName = f"{self.counter} "
        self.counter += 1

        if message.photo:
            fileName += ".jpg"
        elif file.name:
            fileName += file.name 

        await message.download_media(file=f"{self.path}/{fileName}")

    def emptyBigFilesLog(self) -> None:
        with open(f"{self.path}/bigfiles.csv", 'a') as f:
            while self.skippedStack:
                messageID: int = self.skippedStack.pop()
                f.write(f"{messageID}\n")

class Progress:
    def __init__(self, totalMessages: int) -> None:
        self.MbToByte:             int   = 1024 ** 2
        self.sizeInMb:             int   = 0
        self.timeStart:            float = time.perf_counter()
        self.totalMessages:        int   = totalMessages
        self.totalMessagesPercent: int   = max(totalMessages//100, 1)
        self.messageCounter:       int   = 1
        self.lastMessageID:        int   = 1
        self.savedDialogInfo:      bool  = False
  
    def __str__(self) -> str:
        if self.totalMessages <= 0:
            return "Progress: N/A"

        progressPercent: float      = min(self.messageCounter / self.totalMessages * 100, 100)
        progressInTens:  int        = int (progressPercent // 10)
        progressBar:     str        = ('█' * progressInTens + '░' * (10 - progressInTens))
        elapsedTime:     float      = time.perf_counter() - self.timeStart
        ETAElapsed:      str        = formatETA(elapsedTime)
        messageRate:     float      = 0.0
        downloadRate:    float      = 0.0
        remainingTime:   float      = 0.0

        if elapsedTime > 0:
            messageRate             = self.messageCounter / elapsedTime
            downloadRate            = f"{self.sizeInMb / elapsedTime:.3f}MB/s"
            if messageRate > 0:
                remainingTime       =  (self.totalMessages - self.messageCounter) / messageRate

        ETARemaining:         str   = formatETA(remainingTime)
        messageRateFormatted: str   = f"{self.messageCounter / elapsedTime:.3f}msg/s"
        sizeInMBFormatted:    str   = f"{self.sizeInMb:.3f}MB"

        status = (
            f"Message {self.messageCounter:^14} | "
            f"{ETAElapsed:^14} | "
            f"{sizeInMBFormatted:^8} | "
            f"{messageRateFormatted:^8} | "
            f"{downloadRate:^8} | "
            f"ETA: {ETARemaining:^14}\n"
            f"Progress: {progressBar}..."
        )

        return status

    def checkProgress(self) -> None:
        if self.messageCounter % self.totalMessagesPercent == 0:
            clearLastLine(2)
            print(self)

class Errors:
    def __init__(self, path: str, progress: Progress, fileHanlder: File) -> None:
        self.path           = path
        self.progressClass  = progress
        self.fileClass      = fileHanlder
    
    async def handle(self, error) -> None:
        saveCheckpoint(self.progressClass.lastMessageID, 
                       self.progressClass.messageCounter,
                       self.fileClass.counter,
                       self.progressClass.savedDialogInfo,
                       self.path,
                       self.progressClass.timeStart)

        self.fileClass.emptyBigFilesLog()

        with open("dialogs/erros.txt", 'a') as f:
            f.write(
                f"Error occured in {self.path} "
                f"at message {self.progressClass.lastMessageID}:\n"
                f"{error}\n\n"
            )

        if isinstance(error, FloodWaitError):
            print(f"You've been rate limited for {error.seconds}s")
            await asyncio.sleep(error.seconds)
            clearLastLine()

def formatETA(seconds: float) -> str:
    seconds = int(seconds)
    
    d: int = seconds // (3600 * 24)
    h: int = (seconds % (3600 * 24)) // 3600
    m: int = (seconds % 3600) // 60
    s: int = seconds % 60

    if d:
        return f"{d}d {h}h {m}m {s}s"
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
        
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
        print(f"Error: {e} occurred.")
        return

    totalMessages: int           = (await client.get_messages(dialog, limit=0)).total
    fileHandler:   File          = File(PATH, config.fileSizeThresholdInBytes)
    progress:      Progress      = Progress(totalMessages)
    errorHandler:  Errors        = Errors(PATH, progress, fileHandler)

    users                        = set()
    dialogSavedCheckpoint        = getCheckpoint(PATH)
    if dialogSavedCheckpoint:
        progress.lastMessageID   = dialogSavedCheckpoint[0]
        progress.messageCounter  = dialogSavedCheckpoint[1]
        fileHandler.counter      = dialogSavedCheckpoint[2]
        progress.savedDialogInfo = dialogSavedCheckpoint[3]
        progress.timeStart      -= dialogSavedCheckpoint[4]
    
    print(progress)

    try:
        with open(f"{PATH}/TextMessages.csv", 'a') as texts, \
             open(f"{PATH}/Reactions.csv", 'a') as reactions:
            CSVMessagesWrtier = csv.writer(texts)
            CSVReactionsWriter = csv.writer(reactions)

            async for message in client.iter_messages(dialog.entity, reverse=True, offset_id=progress.messageCounter):
                # for writing into the file at once
                messagesRow = []
                if config.texts:
                    messagesRow.append(message.id)

                    await userIdHandler (message, messagesRow, users)
                    
                    await forwardHanlder (message, messagesRow, users)
                    
                    await replyHandler (message, messagesRow)

                    await textHandler (message, messagesRow)

                    messagesRow.append(message.date)

                if config.files:
                    await fileHandler.handle(message, messagesRow)
                    if message.file:
                        progress.sizeInMb += message.file.size / progress.MbToByte

                CSVMessagesWrtier.writerow(messagesRow)

                if config.reactions:
                    await reactionHandler(message, CSVReactionsWriter, dialog)

                progress.messageCounter += 1
                progress.lastMessageId   = message.id
                
                progress.checkProgress()

            if config.dialogInfo and not progress.savedDialogInfo:
                await getGroupOrChannelInfo(dialog, PATH, users, errorHandler)
                progress.savedDialogInfo = True

            if config.userInfo:
                await usersHandler(users, PATH, errorHandler)

            if config.files:
                fileHandler.emptyBigFilesLog()

            saveCheckpoint(progress.lastMessageID, progress.messageCounter, 
                           fileHandler.counter, progress.savedDialogInfo, 
                           PATH, progress.timeStart)
            clearLastLine(3)
            print(f"Done archiving {dialog.name}!")

    except FloodWaitError as e:
        await errorHandler.handle(e)

    except (KeyboardInterrupt, asyncio.CancelledError) as e:
        clearLastLine(3)
        print("Please wait a moment while the saving the checkpoint")

        fileHandler.emptyBigFilesLog()

        saveCheckpoint(progress.lastMessageID, progress.messageCounter, 
                       fileHandler.counter, progress.savedDialogInfo, 
                       PATH, progress.timeStart)

        if config.userInfo:
            with open(f"{PATH}/Users.csv", 'w') as f:
                CSVUserWriter = csv.writer(f)
                for user in users:
                    CSVUserWriter.writerow([user])

        clearLastLine()
        print("Done!")
        exit(0)

    except Exception as e:
        await errorHandler.handle(e)

async def getGroupOrChannelInfo(dialog, PATH, users, errorHandler: Errors):
    dialog = dialog.entity    
    infoPath = f"{PATH}/Dialog Info"
    os.makedirs(infoPath, exist_ok=True)

    await getFullRequest(dialog, infoPath)

    await getPhotoInfo(dialog, infoPath)

    await addUsersToSet(dialog, users, errorHandler)

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

async def addUsersToSet(dialog, users, errorHandler: Errors):
    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)
    except (ChatAdminRequiredError, ChannelPrivateError, Exception) as e:
        await errorHandler.handle(e)

async def usersHandler(users, path, errorHandler: Errors):
    if not users: return
    try:
        with open(f"{path}/Users.csv", 'r', newline='', encoding='utf-8') as f:
            CSVReader = csv.reader(f)
            readUsers = list(CSVReader)
            for user in readUsers:
                if user not in users:
                    users.add(int(user))

        with open(f"{path}/Users.csv", 'w') as f:
            CSVWriter = csv.writer(f)
            row = list(users)
            CSVWriter.writerows(row)
    except OSError as e:
        await errorHandler.handle(e)

    for user in users:
        if isinstance(user, int):
            await getUserInfo(user, errorHandler)

async def getUserInfo(userId, errorHandler: Errors):
    user = await client.get_entity(userId)
    filePath = f"dialogs/users/{userId}"

    try:
        os.mkdir(filePath)
    except (OSError, Exception) as e:
        await errorHandler.handle(e)
        return
    
    await getFullRequest(user, filePath)
    await getPhotoInfo(user, filePath)

async def calculateDialogSpace(dialog, config: Config):
    progress: Progress = Progress(dialog)

    try:
        progress.print()

        async for message in client.iter_messages(dialog.entity):
            progress.messageCounter += 1
            progress.checkProgress()
               
            if message.file and message.file.size < config.fileSizeThresholdInBytes:
                progress.sizeInMb += message.file.size / progress.MbToByte

        clearLastLine(3)
        print(f"Dialog {dialog.title} will take about {progress.sizeInMb:.3f}MB")
        return progress.sizeInMb

    except FloodWaitError as e:
        print(f"You've been rate limited for {e.seconds}s")
        await asyncio.sleep(e.seconds)

def saveCheckpoint(lastMessageID: int, messageCounter: int, 
                   fileCounter: int, flagOfGetDialogInfo: bool, 
                   dialogPath: str, timeStart: float) -> None:
    dialog = []
    try:
        with open(f"{dialogPath}/CheckPoint.json", 'r') as f:
            dialog = json.load(f) 
            # if any of the inputs is 0 means don't change it, like if you haven't parsed the dialog info yet
            if lastMessageID:       dialog[0] = lastMessageID
            if messageCounter:      dialog[1] = messageCounter
            if fileCounter:         dialog[2] = fileCounter
            if flagOfGetDialogInfo: dialog[3] = flagOfGetDialogInfo
            if timeStart:           dialog[4] = time.perf_counter() - timeStart
    except (FileNotFoundError, json.JSONDecodeError):
        dialog = [lastMessageID, messageCounter, fileCounter, flagOfGetDialogInfo, time.perf_counter() - timeStart]
        
    with open(f"{dialogPath}/CheckPoint.json", 'w') as f:
        f.write(json.dumps(dialog))

def getCheckpoint(dialogPath: str) -> list:
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
    parser.add_argument("-c", "--check-size", action="store_true", help="check dialog size beforehand")
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

    config.checkSize = args.check_size
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
        ans = await asyncio.to_thread(input, f"Do you want to archive {dialog.name}? (y) ")
        if (ans == 'y'):
            clearLastLine()
            if config.checkSize:
                print(f"Calculating the size of {dialog.name}...")
                await calculateDialogSpace(dialog)

            if isinstance(dialog.entity, (types.Chat, types.Channel, types.User)):
                print(f"Archiving {dialog.name}...")
                await archiveGroup(dialog, config)
            else:
                print("Error: can't archive this!")
        else:
            clearLastLine()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())