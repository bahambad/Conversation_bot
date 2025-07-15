from aiogram import Router, F, types
from aiogram.enums import ParseMode

router = Router(name=__name__)



# Функция ответа на случай непонимания со стороны пользователей
"""
Эти функции объясняют пользователю какого типа сообщения нужно отправлять
чтобы бот их обработал, на случай если пользователь перепутал и отправил ГС или Кружок
"""

@router.message(F.voice)
async def handleer_for_voice(message: types.Audio):
    answer_voice = """⛔️ Please send an <b>AUDIO FILE</b>.  
I don't process voice messages."""
    await message.answer(text=answer_voice, parse_mode=ParseMode.HTML)


@router.message(F.video_note)
async def handleer_for_video_note(message: types.VideoNote):
    answer_video_note = """⛔️ Please send just an ordinary <b>VIDEO</b>.  
I don't process video notes."""
    await message.answer(text=answer_video_note, parse_mode=ParseMode.HTML)
