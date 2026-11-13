from contextlib import suppress

from aiogram import Bot, Router, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender

from modules.avangard_defs import avangard_video, is_number
from modules.jobs import download_tg_file, heavy_job, job_dir, report_errors
from modules.paths import AUDIO_DIR
from states import Avangard

router = Router(name=__name__)

SONGS = ["AVANGARD", "avangardik"]
# Допустимая громкость песни, в процентах
MAX_VOLUME = 1000

INVALID_NUMBER_TEXT = """🔢 <b>Please send a number.</b>
I didn’t understand your response — just reply with a valid number."""
INVALID_VOLUME_TEXT = f"""🔢 <b>Please send a number from 0 to {MAX_VOLUME}.</b>"""
WAITING_TEXT = "✅ I got it.\nPlease wait a moment..."


# Функция Авангарда
@router.message(Command("avangard"))
async def handle_avangard(message: types.Message, state: FSMContext):
    await state.set_state(Avangard.volume)
    avangard_text = """🔊 Please send me the <b>volume level</b> (e.g., <code>100</code> = 100%).
Just reply with a number.

Send /cancel to stop."""

    await message.answer(text=avangard_text,
                         parse_mode=ParseMode.HTML)


@router.message(Avangard.volume, F.text)
async def volume(message: types.Message, state: FSMContext):
    if not is_number(message.text):
        await message.answer(text=INVALID_NUMBER_TEXT, parse_mode=ParseMode.HTML)
        return

    volume_num = int(message.text)
    if not 0 <= volume_num <= MAX_VOLUME:
        await message.answer(text=INVALID_VOLUME_TEXT, parse_mode=ParseMode.HTML)
        return

    await state.set_state(Avangard.song)
    await state.update_data(volume_num=volume_num)
    song_text = """🎵 Okay, I got it!
Now, which song do you want?

Please send:
<code>1</code> — for the <b>first</b> song
<code>2</code> — for the <b>second</b> song

Just reply with the number."""
    await message.answer(text=song_text, parse_mode=ParseMode.HTML)


@router.message(Avangard.volume)
async def invalid_volume(message: types.Message):
    await message.answer(text=INVALID_NUMBER_TEXT, parse_mode=ParseMode.HTML)


@router.message(Avangard.song, F.text)
async def song(message: types.Message, state: FSMContext):
    if not is_number(message.text):
        await message.answer(text=INVALID_NUMBER_TEXT, parse_mode=ParseMode.HTML)
        return

    await state.set_state(Avangard.transforming)
    await state.update_data(song_num=int(message.text))
    song_text = """✅ Okay, I got it.  
📹 Now send me a <b>video note</b> and I'll add the song to it."""
    await message.answer(text=song_text, parse_mode=ParseMode.HTML)


@router.message(Avangard.song)
async def invalid_song(message: types.Message):
    await message.answer(text=INVALID_NUMBER_TEXT, parse_mode=ParseMode.HTML)


@router.message(F.video_note, Avangard.transforming)
async def avangard_note(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # Номер песни ограничиваем диапазоном списка
    song_number = min(max(data["song_num"] - 1, 0), len(SONGS) - 1)
    volume_parameter = data["volume_num"]
    audio_path = AUDIO_DIR / f"{SONGS[song_number]}.mp3"
    chat_id = message.chat.id

    async with report_errors(bot, chat_id):
        async with heavy_job(message.from_user.id):
            waiting_message = await message.answer(text=WAITING_TEXT, parse_mode=ParseMode.HTML)
            try:
                with job_dir() as workdir:
                    async with ChatActionSender(bot=bot, chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO_NOTE):
                        source_path = workdir / "input.mp4"
                        output_path = workdir / "avangard.mp4"
                        await download_tg_file(bot, message.video_note.file_id,
                                               message.video_note.file_size, source_path)

                        await avangard_video(source_path, output_path, audio_path, volume_parameter)

                        # Отправляем обратно как video_note
                        await message.answer_video_note(video_note=types.FSInputFile(path=output_path))
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()

            # Состояние сбрасываем только после успеха: при ошибке кружок можно отправить ещё раз
            await state.clear()
