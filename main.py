import json, asyncio, os, csv, time
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    MessageService,
    MessageActionChatAddUser,
    MessageActionChatDeleteUser,
    MessageActionChatJoinedByLink,
    MessageActionPinMessage,
    MessageActionChatEditTitle,
    MessageActionChatEditPhoto,
    MessageActionChatCreate
)

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
async def replyHandler(message, messagesRow):
    # check if this message is a reply to another
    if not message.is_reply:
        messagesRow.append('0')
        return
    reply = await message.get_reply_message()
    messagesRow.append(str(reply.id))

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
    messagesRow.append(str(forward.from_id))
    users.add(forward.from_id)
    
async def textHandler(message, messagesRow):
    # check for text
    if message.text:
        messagesRow.append(f"{message.text}")
    elif isinstance(message, MessageService):
        action = message.action
        if isinstance(action, MessageActionPinMessage):
            messagesRow.append(f"a messaage was pinned")
        elif isinstance(action, MessageActionChatAddUser):
            messagesRow.append(f"{action.users} was added")
        elif isinstance(action, MessageActionChatJoinedByLink):
            messagesRow.append(f"{action.inviter_id} joined")
        elif isinstance(action, MessageActionChatDeleteUser):
            messagesRow.append(f"{action.user_id} was kicked/left")
        elif isinstance(action, MessageActionChatEditPhoto):
            messagesRow.append(f"chat photo changed")
        elif isinstance(action, MessageActionChatEditTitle):
            messagesRow.append(f"chat title changed to {action.title}")
        elif isinstance(action, MessageActionChatCreate):
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
        for react in reactions.results:
            reactionsRow.append(react.reaction)
            reactionsRow.append(react.count)
        CSVReactionsWriter.writerow(reactionsRow)
        return

    # For groups or chats
    for react in reactions.recent_reactions:
        reactionsRow.append(react.reaction.emoticon)
        reactionsRow.append(react.date)
        reactionsRow.append(react.peer_id.user_id)
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
        texts = open(f"{PATH}/Text messages.csv", 'w')
        reactions = open(f"{PATH}/Reactions.csv", 'w')
        CSVMessagesWrtier = csv.writer(texts)
        CSVReactionsWriter = csv.writer(reactions)
    except OSError as e:
        print(f"Error making the folders/files: {e}")
        exit()

    users = set()
    fileCounter = 1

    async for message in client.iter_messages(dialog.entity, reverse=True):
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

    texts.close()    

# TODO: Not done!
# TODO: rate limit handler
async def getDialogInfo(client, dialog, PATH):
    with open(f"{PATH}/Dialog Info") as f:
        messagesRow = []
        messagesRow.append(str(dialog.id))
        messagesRow.append(f"{dialog.name}")
        if not dialog.is_user:
            messagesRow.append(dialog.participants_count)

        f.write(messagesRow)
        pass
    # async for photo in client.iter_profile_photos():

    


async def main():
    print("Started...")
    os.makedirs("dialogs", exist_ok=True)
    dialogCounter = 1

    async for dialog in client.iter_dialogs():
        if (input(f"Do you want to check {dialog.name}?") == 'y'):
            await calculateDialogSpace(dialog)
        # if dialog.is_group:
        #     await archiveGroup(dialog, dialogCounter)
        # dialogCounter += 1

with client:
    client.loop.run_until_complete(main())
