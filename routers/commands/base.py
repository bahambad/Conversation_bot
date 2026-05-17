from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import LinkPreviewOptions, ReplyKeyboardRemove
from aiogram.utils import markdown
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.payload import decode_payload

router = Router(name=__name__)

# Функция старта
@router.message(CommandStart(deep_link=True))
async def handle_start(message: types.Message, command: CommandObject):
    # args = command.args
    # payload = decode_payload(args)
    # await message.answer(payload)
    url ="https://sdmntpreastus2.oaiusercontent.com/files/00000000-60cc-51f6-9d6b-4c8d1e75ceac/raw?se=2025-04-05T14%3A13%3A54Z&sp=r&sv=2024-08-04&sr=b&scid=0dd2fe23-ebd7-5f9e-8874-d61e7e1e10ba&skoid=3f3a9132-9530-48ef-96b7-fee5a811733f&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-04-05T08%3A07%3A23Z&ske=2025-04-06T08%3A07%3A23Z&sks=b&skv=2024-08-04&sig=fTrYnU6l%2BLQVSzlNgFfmAmHuNkpq5rh0EGR4E5wjmic%3D"
    hello_text = f"""{markdown.hide_link(url)}👋 Hello, <b>{message.from_user.full_name}</b>!  
🎧 Welcome to the <b>Audio & Video Conversion Bot</b> 🔁

Here you can easily convert:  
🎵 <b>Audio files</b> → <i>Voice messages</i>  
🎬 <b>Video files</b> → <i>Video notes</i>
🎧 <b>Video notes</b> → <i>Voice messages</i>

❓ Type /help to learn how to use the bot.
"""
    await message.answer(text=hello_text,
                         parse_mode=ParseMode.HTML,
                         reply_markup=ReplyKeyboardRemove(),
                         link_preview_options=LinkPreviewOptions(
                             is_disabled=False,
                             url=url,
                             show_above_text=True,
                         )
                    )


# Функция помощи
@router.message(Command("help"))
async def handle_help(message: types.Message):
    help_text = """🔄 This bot converts:  
🎵 <b>MP3 audio files</b> → <i>Voice messages</i>  
🎬 <b>MP4 videos</b> → <i>Video notes</i>
🎧 <b>Video notes</b> → <i>Voice messages</i>

📤 Just upload your file and pick an option you need.
ℹ️ <b>Note:</b> If you want to create a <b>video note</b>, the video must be shorter than ⏱️ <b>60 seconds</b>.


⚠️ <b>ATTENTION!</b> Audio and video files must be under <b>20 MB</b>! ⚠️
"""
    await message.answer(text=help_text,
                         parse_mode=ParseMode.HTML)
