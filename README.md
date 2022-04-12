# Environment Variables
In order for the script to work, there must be three environment variables present:
- API_KEY
- CHAT_ID
- CHAT_ID_ERROR

## Create an .env-file
The file should be in the same directory as the the script.
```ini
API_KEY = value
CHAT_ID = value
CHAT_ID_ERROR = value
```

## API_KEY
Search for the bot @BotFather. Then type /start, /newbot and so on. At the last copy the token and set its to the environment variable API_KEY.

## chat-IDs
In order to get your chat-ID, search in Telegram for @RawDataBot, type /start and get the value search the json-String vor the value `dict["message"]["chat"]["id"]`. To do this, it's necessary to add a username first in the Telegram-Settings.