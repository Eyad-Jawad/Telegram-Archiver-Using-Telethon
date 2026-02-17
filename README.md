# Telegram Archiver Using Telethon
## The things it archives
For now it only archives messages, files, some service messages, and date
## How To Use It
License: MIT
You have to get the API keys from telegram.org and then set them using the command:  
```

setx TELEGRAM_API_KEY "123456"
setx TELEGRAM_API_HASH "abcdefg" 

```
After that, you just have to run the command
### Archive Schema
``` 

message_id, sender_id, file_id, file_relative_id, file_forwarded (if bigger than 100mb), replyed_to_message_id, forward_from_user_id, forward_from_username, message_text, message_date  

```
For each one of those, if it doesn't exist (like a message not forwarded) it'll default to `0`

### What Did I Learn
I'm still learning and this project is far from done, as a matter of fact, this is so-not-done that I'm hesitant to share, but it'll take some time for me to navigate the telethon docs as to archive most important stuff, and make it more user-freindly or something, idk