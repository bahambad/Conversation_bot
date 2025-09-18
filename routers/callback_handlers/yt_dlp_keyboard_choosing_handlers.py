import os

from aiogram import F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender

from keyboards.yt_dlp_keyboard import UrlOfVideoCdData
from modules.yt_downloads import check_video_size, download_audio_from_youtube, download_video_from_youtube
from routers.video_processing import url_storage

router = Router(name=__name__)

@router.callback_query(UrlOfVideoCdData.filter(F.operation == "audio"))
async def handle_audio_yt_dlp(call: CallbackQuery, callback_data: UrlOfVideoCdData):
    message = call.message
    await call.answer()
    url = url_storage.pop(callback_data.url_id, None)
    await message.delete()
    text = """Okay, i got it. Now i'm going to download audio from this video"""
    msg = await message.answer(text=text,
                               parse_mode=ParseMode.HTML,
                               )

    action_sender = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_DOCUMENT,
    )
    if check_video_size(url, 1080, max_size_mb=20):
        try:
            outpath = download_audio_from_youtube(url)
            if outpath == False:
                error_text = "Error. I can't download it for some reason."
                await message.answer(text=error_text,
                                     parse_mode=ParseMode.HTML,
                                     )
                await msg.delete()
                return
            # Показываю что аудио уже загружается
            async with action_sender:
                await message.bot.send_chat_action(
                    chat_id=message.chat.id,
                    action=ChatAction.UPLOAD_DOCUMENT,
                )

            # Отправляем аудио
            await message.answer_audio(audio=types.FSInputFile(path=outpath))

            await msg.delete()
            os.remove(outpath)
        except:
            error_text = f"""⛔️ <b>Failed to receive the file.</b>  
        The file is too big. It might be smaller than <b>20 MB</b>."""
            await message.answer(text=error_text,
                                 parse_mode=ParseMode.HTML)
            await msg.delete()
            return
    else:
        big_video_text = """⛔️ <b>Failed to receive the file.</b>  
        The file is too big. It might be smaller than <b>20 MB</b>."""
        await message.answer(text=big_video_text,
                                 parse_mode=ParseMode.HTML)
        await msg.delete()
        return



@router.callback_query(UrlOfVideoCdData.filter(F.operation == "video"))
async def handle_video_yt_dlp(call: CallbackQuery, callback_data: UrlOfVideoCdData):
    await call.answer()
    message = call.message
    url = url_storage.pop(callback_data.url_id, None)
    await call.message.delete()
    text = """Okay, i got it. Now i'm going to download this video"""
    msg = await message.answer(text=text,
                               parse_mode=ParseMode.HTML,
                               )
    action_sender = ChatActionSender(
        bot=message.bot,
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_VIDEO,
    )
    size_okay = check_video_size(url, 1080, max_size_mb=20)
    if size_okay:
        try:
            outpath = download_video_from_youtube(url)
            if outpath == False:
                error_text = "Error. I can't download it for some reason."
                await message.answer(text=error_text,
                                     parse_mode=ParseMode.HTML, )
                await msg.delete()
                return
                # Показываю что видео уже загружается
            async with action_sender:
                await message.bot.send_chat_action(
                    chat_id=message.chat.id,
                    action=ChatAction.UPLOAD_VIDEO,
                )

            # Отправляем аудио
            await message.answer_video(video=types.FSInputFile(path=outpath))

            await msg.delete()
            os.remove(outpath)

        except:
            error_text = """⛔️ <b>Failed to receive the file.</b>  
    The file is too big. Please upload a file smaller than <b>20 MB</b>."""
            await message.answer(text=error_text,
                                 parse_mode=ParseMode.HTML)
            await msg.delete()
            return
    else:
        big_video_text = """⛔️ <b>Failed to receive the file.</b>  
    The file is too big. Please upload a file smaller than <b>20 MB</b>."""
        await message.answer(text=big_video_text,
                             parse_mode=ParseMode.HTML)
        await msg.delete()
        return