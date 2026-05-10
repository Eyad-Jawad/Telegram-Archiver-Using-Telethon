import os, csv
from telethon import functions, types
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError
from objects import errors
        
async def userIdHandler(message, messagesRow, users):
    # check for the id of the user to add to the message
    if message.post_author:
        messagesRow[1] = message.post_author
        return
    elif not message.sender_id: 
        messagesRow[1] = 0
        return

    messagesRow[1] = message.sender_id
    # check if the sender is not saved
    if message.sender_id not in users:
        users.add(message.sender_id)

async def getGroupOrChannelInfo (
        client, 
        dialog, 
        PATH, 
        users, 
        errorHandler: errors.Errors
    ):

    dialog = dialog.entity    
    infoPath = f"{PATH}/Dialog Info"
    os.makedirs(infoPath, exist_ok=True)

    await getFullRequest(client, dialog, infoPath)

    await getPhotoInfo(client, dialog, infoPath)

    await addUsersToSet(client, dialog, users, errorHandler)

async def getFullRequest(client, dialog, Path):
    with open(f"{Path}/info.txt", 'w') as f:
        fullRequest = None

        if isinstance(dialog, types.Channel):
            fullRequest = await client(functions.channels.GetFullChannelRequest(dialog))

        elif isinstance(dialog, types.User):
            fullRequest = await client(functions.users.GetFullUserRequest(dialog))

        else:
            fullRequest = await client(functions.messages.GetFullChatRequest(dialog))

        f.write(fullRequest.stringify())

async def getPhotoInfo(client, dialog, Path):
    with open(f"{Path}/PhotoInfo.csv", 'w') as f:
        CSVInfoWriter = csv.writer(f)
        photoDataRow = []

        async for photo in client.iter_profile_photos(dialog):
            await client.download_media(photo, file=Path)
            photoDataRow.append(photo.date)
        CSVInfoWriter.writerow(photoDataRow)

async def addUsersToSet(client, dialog, users, errorHandler: errors.Errors):
    try:
        async for user in client.iter_participants(dialog):
            if user.id not in users:
                users.add(user.id)
    except (ChatAdminRequiredError, ChannelPrivateError, Exception) as e:
        await errorHandler.handle(e)

async def usersHandler(client, users, path, errorHandler: errors.Errors):
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
        await getUserInfo(client, user, errorHandler)

async def getUserInfo(client, userId, errorHandler: errors.Errors):
    user = await client.get_entity(userId)
    userType = type(user).__name__
    filePath = f"dialogs/{userType}s/{userId}"

    try:
        os.mkdir(filePath)
    except OSError as e:
        await errorHandler.handle(e)
        return
    
    await getFullRequest(user, filePath)
    await getPhotoInfo(user, filePath)