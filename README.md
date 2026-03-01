# Telegram Archiver Using Telethon
## The things it archives

It archives:

```

dialogs /
    dialog type /
        dialog id /
            text messages
            reactions
            users' ids
            state (checkpoint)
            files /
                photos, videos, documents, individual stickers, voice recordings, music, etc.
            dialog info /
                info file (telethon full request)
                dialog photos
                photo info (has the dates of the pfps)

```

## How To Use It

License: MIT  
Author: Eyad Jawad

### WARNING:

DO NOT RUN THIS PROGRAM AGRESSIVELY!  
I haven't tried running the program for extended periods of time, but if you run it for say, days, you might be rate limited multiple times, even though the program handles rate limit, too much rate limit might very well get your account banned, so I'd suggest you be careful when using it for large dialogs.

### Setting The API keys

You have to get the API keys from telegram.org and then set them in the .env:  

```

TELEGRAM_API_KEY "123456"
TELEGRAM_API_HASH "abcdefg" 

```
This is probably the safest way possible to ensure that your keys don't get leaked, I would never put mine straight into the program, you could read them from a file, but don't forget to add it to the gitignore.

### Arguments
`c`, `--check-size`: `check dialog size beforehand`  
`-a`, `--archive-all`: `archive everything`  
`-t`, `--archive-text`: `archive text messages (including forward, reply, edit, and sender_id)`  
`-r`, `--archive-reactions`: `archive message reactions`  
`-d`, `--archive-dialog-info`: `archive dialog info like title, bio, pfps, and etc.`  
`-u`, `--archive-user-info`: `archive info of users in a dialog, like name, bio, pfps, and etc.`  
`-f`, `--archive-file`: `archive files, like photos, videos, documents, and etc. with a size threshold (default: 100MB)`  
`-b`, `--archive-big-files`: `archive all files ignoring the default of 100MB`  
`-s`, `--size-threshold` : `the size threshold for files (default: 100MB)`    
After that, you just have to run the command:  

```

python main.py -t -r -f -s 10

```
## Archiving Schemas
### TextMessages.csv:

``` 

message_id, sender_id, file_forwarded (if bigger than size-threshold), replyed_to_message_id, forward_from_user_id, forward_from_username, message_text, message_date, file_id, file_relative_id  

```

### Reactions.csv

This one is split into two genres, one for channels, and another one for chats where you can see the users who reacted.  
Channels:

```

message_id, reaction, reaction_count

```

Chats:

```

message_id, reactor_id, date_of_reacting, reaction

```

### Users.csv
this one is simple, it just has users ids

```

user_id

```

### CheckPoint.json

```

message_count, file_count, saved_dialog_info, elapsed_time

```

### BigFiles.csv

```

message_id

```

### PhotoInfo.csv

```

photo_date

```

For each one of those, if it doesn't exist (like a message not forwarded) it'll default to `0`

### What Did I Learn

I learnt a lot about file managment, and how to parse things in general, but the coolest thing if you ask me is the progress bar, that is cool.  
This project did take a good chunk of time to finish, or at least get it to work, and I did it mainly because I love archiving things locally, it works pretty well in my opinion.  
I also learnt a good amount of error handling, while it is not sublime, error handling is good here.  
I'd like to add a way to reverse the process and get a GUI out of it, I've seen that on discord archivers, I'd also want to add a way to compress stuff, like files, or at least do something about them because they take A LOT of space.  
All in all, I'm pretty much satisfied with this project, it took me about 50h? idk, but I do feel like I'm missing some features.  
I have listed a good list of todos and fixme in the code, I might do them one day...? idk, I hopne it'll be good, inshallah.  
Thank you for reading -Eyad.