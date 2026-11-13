# Conversation Bot

A Telegram bot that converts audio and video between Telegram formats and downloads media by link.
Built with [aiogram 3](https://docs.aiogram.dev/), [FFmpeg](https://ffmpeg.org/) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

| You send | You get |
|---|---|
| An audio file | A voice message |
| A video or a video note | A voice message or an MP3 file (you choose with a button) |
| A video (privileged users only) | A video note |
| An `https://` link to a supported site | The video (MP4) or its audio (MP3) |
| `/avangard`, then a video note | The same video note with a song mixed in |
| `/avangard`, then a video (privileged users only) | The video cropped to a video note, with a song mixed in |

Audio downloaded by link is sent with the channel name as the performer and the video thumbnail as the cover
(the channel avatar is used when there is no thumbnail).

Voice messages are not processed: the bot replies with a hint.

### Commands

| Command | Description |
|---|---|
| `/start` | Greeting |
| `/help` | Short usage guide |
| `/avangard` | Add one of the bundled songs to a video note: the bot asks for the volume, the song number and then the video note (or a video, for privileged users) |
| `/cancel` | Leave the current `/avangard` dialog |
| `/ban <user_id>` | Admin only. Block a user |
| `/unban <user_id>` | Admin only. Unblock a user |
| `/check` | Admin only. Show blocked users |

The ban list is kept in memory and is cleared when the bot restarts.

### Limits

- Files up to **20 MB**, both uploaded and downloaded by link.
- Videos turned into video notes must be shorter than **60 seconds**.
- Playlists and live streams are not downloaded.
- One conversion or download per user at a time, two for the whole bot; other requests wait in a queue.
- Flood protection: users who send messages or press buttons too fast are ignored for a few seconds.

## Configuration

The bot reads its settings from environment variables or from a `.env` file in the project root.
Copy the example and fill it in:

```bash
cp env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | yes | Bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN` | yes | Numeric Telegram id of the admin |
| `PRIVILEGED_USERS` | no | Comma separated ids of privileged users. They get the features that are not open to everyone because of server load or abuse risk; currently that is turning videos into video notes. Empty by default |
| `ALLOWED_DOMAINS` | no | Comma separated sites that links may point to. Replaces the built-in list (see below) |

Built-in list of sites for downloading by link (subdomains included): `youtube.com`, `youtu.be`, `tiktok.com`,
`instagram.com`, `twitter.com`, `x.com`, `vk.com`, `vkvideo.ru`, `rutube.ru`, `soundcloud.com`, `vimeo.com`, `twitch.tv`.

## Running locally

Requirements: Python 3.10 or newer (the Docker image uses 3.11) and FFmpeg (`ffmpeg` and `ffprobe`) in `PATH`.

```bash
python3.11 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python main.py
```

On Windows use `.venv\Scripts\pip` and `.venv\Scripts\python` instead.

## Running with Docker

The image already contains FFmpeg. The `.env` file is not copied into the image, so mount it when starting the container:

```bash
docker build -t conversation-bot .
```

```bash
docker run -d --name conversation-bot --restart unless-stopped -v "$(pwd)/.env:/usr/src/app/.env:ro" conversation-bot
```

Alternatively, pass the settings as environment variables with `-e BOT_TOKEN=... -e ADMIN=...`.

To see the logs:

```bash
docker logs -f conversation-bot
```

## Project structure

```
main.py                  entry point: dispatcher, middleware, polling
states.py                FSM states
middlewares/antiflood.py flood protection for messages and buttons
routers/                 handlers
  commands/              /start, /help, /cancel, /avangard, admin commands
  callback_handlers/     inline button handlers (video operations, downloads by link)
  filters/               admin and ban filters
  audio_processing.py    audio file -> voice message
  video_processing.py    incoming videos and links
keyboards/               inline keyboards
modules/                 FFmpeg and yt-dlp wrappers, temp files, limits, permissions
audio/                   songs for /avangard
```

Temporary files are stored in `downloads/`, one folder per request; each folder is removed when the request finishes,
and the whole directory is cleaned on startup.
