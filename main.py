import json, asyncio, os, csv
from telethon import TelegramClient, functions, types
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


async def userIdHandler(message, row, users):
    # check for the id of the user to add to the message
    if message.sender: 
        row.append(str(message.sender.id))
        # check if the sender is not saved
        if message.sender.id not in users:
            users.add(message.sender.id)
    else:
        row.append('0')

async def fileHanlder(message, row, fileCounter, FILE_PATH):
    isFile = 0
    if not message.file:
        row.append('0')
        row.append('0')
        row.append('0')
    else:
        file = message.file
        # photos don't work with file id in telethon
        if message.photo:
            file = message.photo

        fileName = f"{fileCounter} "
        if message.file.name:
            fileName += message.file.name

        row.append(str(file.id))
        row.append(str(fileCounter))
        isFile = 1
        # if the file is bigger than 100mb, don't download it
        if message.photo or file.size < (1024 ** 2) * 100:
            await message.download_media(file=f"{FILE_PATH}/{fileName}")
            row.append('0')
        else: 
            # keep log of files not downloaded
            await message.forward_to("me")
            row.append('1')
    return isFile

async def replyHandler(message, row):
    # check if this message is a reply to another
    if not message.is_reply:
        row.append('0')
    else:
        reply = await message.get_reply_message()
        row.append(str(reply.id))

async def forwardHanlder(message, row, users):
    forward = message.forward
    if not forward:
        row.append('0')
        row.append('0')
    else:
        row.append(f"{forward.from_name}")
        if not forward.from_id:
            row.append('0')
        else:
            row.append(str(forward.from_id))
            users.add(forward.from_id)
    
async def textHandler(message, row):
    # check for text
    if message.text:
        row.append(f"{message.text}")
    elif isinstance(message, MessageService):
        action = message.action
        if isinstance(action, MessageActionPinMessage):
            row.append(f"a messaage was pinned")
        elif isinstance(action, MessageActionChatAddUser):
            row.append(f"{action.users} was added")
        elif isinstance(action, MessageActionChatJoinedByLink):
            row.append(f"{action.inviter_id} joined")
        elif isinstance(action, MessageActionChatDeleteUser):
            row.append(f"{action.user_id} was kicked/left")
        elif isinstance(action, MessageActionChatEditPhoto):
            row.append(f"chat photo changed")
        elif isinstance(action, MessageActionChatEditTitle):
            row.append(f"chat title changed to {action.title}")
        elif isinstance(action, MessageActionChatCreate):
            row.append(f"{action.title} was created with users: {action.users}")
        else:
            row.append(f"{action} was done.")

    else: 
        row.append("")

# TODO: reactions handler
# TODO: Topic handler
# TODO: use better except
# TODO: Make the code look better
async def archiveGroup(dialog, dialogCounter):
    PATH = f"dialogs/groups/dialog {dialogCounter}"
    FILE_PATH = f"{PATH}/file"

    try:
        os.makedirs (f"{PATH}", exist_ok=True)
        os.makedirs (FILE_PATH, exist_ok=True)
        texts = open(f"{PATH}/Text messages.csv", 'w')
        CSVWrtier = csv.writer(texts)
    except:
        print("Error making the folders/files")
        exit()

    users = set()
    fileCounter = 1

    async for message in client.iter_messages(dialog.entity, reverse=True):
        # for writing into the file at once
        row = []
        row.append(str(message.id))
        
        await userIdHandler (message, row, users)

        fileCounter += await fileHanlder (message, row, fileCounter, FILE_PATH)
        
        await replyHandler (message, row)

        await forwardHanlder (message, row, users)
        
        await textHandler (message, row)
        
        row.append(str(message.date))
        CSVWrtier.writerow(row)

    texts.close()    

# TODO: Not done!
# TODO: rate limit handler
# TODO: Use the csv module
async def getDialogInfo(client, dialog, PATH):
    with open(f"{PATH}/Dialog Info") as f:
        row = []
        row.append(str(dialog.id))
        row.append(f"{dialog.name}")
        if not dialog.is_user:
            row.append(dialog.participants_count)

        f.write(row)
        pass
    # async for photo in client.iter_profile_photos():

    



async def main():
    print("Started...")
    os.makedirs("dialogs", exist_ok=True)
    dialogCounter = 1

    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            await archiveGroup(dialog, dialogCounter)
        dialogCounter += 1

with client:
    client.loop.run_until_complete(main())
