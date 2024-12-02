# AlephBot

AlephBot is a Discord bot designed to assist Hebrew learners. It can add niqqud (vowelization) to Hebrew text using the Nakdan API.

## Features
- Add niqqud to Hebrew text
- Easy-to-use `/vowelize` command

## Setup
1. Clone this repository
2. Create a `.env` file in the root directory and add the following:
```
DISCORD_TOKEN=your_discord_bot_token
NAKDAN_API_KEY=your_nakdan_api_key
```
3. Install the required packages:
```
pip install -r requirements.txt
```
4. Run the bot:
```
python bot.py
```

## Usage
- Invite the bot to your server by [clicking here](https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot)
- Use the `/vowelize` command followed by the text you want to add niqqud to, e.g.:
```
/vowelize אני אוהב ללמוד עברית
```

## Acknowledgements
- [Nakdan API](https://nakdan.dicta.org.il/)