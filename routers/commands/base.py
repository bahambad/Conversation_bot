import html
import logging

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove

from modules.edit_session import close_session
from modules.paths import PICTURES_DIR
from modules.permissions import can_use_fragments, is_privileged
from modules.timecodes import format_timecode
from modules.yt_downloads import MAX_AUDIO_FRAGMENT_DURATION, MAX_FRAGMENT_DURATION

logger = logging.getLogger(__name__)

START_PICTURE = PICTURES_DIR / "conversion.png"
_start_photo_id: str | None = None

router = Router(name=__name__)


def _video_note_status(user_id: int) -> str:
    """Пометка к строке про кружочки: они доступны только привилегированным пользователям (PRIVILEGED_USERS)."""
    return "" if is_privileged(user_id) else " (temporarily unavailable)"


def _fragments_help(user_id: int) -> str:
    """Абзац про фрагменты по таймкодам: его видят только те, кому они доступны."""
    if not can_use_fragments(user_id):
        return ""
    return f"""
✂️ <b>Fragments:</b> send a link and press <b>Video part</b> or <b>Audio part</b>, then send \
the timecodes, for example <code>1:02:30-1:03:10</code>. A fragment can be up to \
<b>{format_timecode(MAX_FRAGMENT_DURATION)}</b> of video or <b>{format_timecode(MAX_AUDIO_FRAGMENT_DURATION)}</b> \
of audio; the source video itself can be of any length.
"""


# Функция старта
@router.message(CommandStart())
async def handle_start(message: types.Message):
    global _start_photo_id

    # Имя пользователя экранируем: символы вроде "<" ломают HTML-разметку
    user_name = html.escape(message.from_user.full_name)
    note_status = _video_note_status(message.from_user.id)
    hello_text = f"""👋 Hello, <b>{user_name}</b>!  
🎧 Welcome to the <b>Audio & Video Conversion Bot</b> 🔁

Here you can easily convert:  
🎵 <b>Audio files</b> → <i>Voice messages</i>  
🎬 <b>Video files</b> → <i>Video notes</i>{note_status}
🎧 <b>Video notes</b> → <i>Voice messages</i>

❓ Type /help to learn how to use the bot.
"""
    try:
        sent = await message.answer_photo(
            photo=_start_photo_id or FSInputFile(path=START_PICTURE),
            caption=hello_text,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove(),
        )
        # Запоминаем file_id, чтобы не загружать картинку заново на каждый /start
        _start_photo_id = sent.photo[-1].file_id
    except (TelegramAPIError, OSError):
        logger.exception("Failed to send the start picture, falling back to text")
        await message.answer(text=hello_text,
                             parse_mode=ParseMode.HTML,
                             reply_markup=ReplyKeyboardRemove())


# Отмена текущего сценария (например, /avangard)
@router.message(Command("cancel"))
async def handle_cancel(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer(text="Nothing to cancel.")
        return
    # Если отменяется сессия монтажа, вместе с ней удаляются и её файлы
    close_session(message.from_user.id)
    await state.clear()
    await message.answer(text="❌ Cancelled.")


# Функция помощи
@router.message(Command("help"))
async def handle_help(message: types.Message):
    note_status = _video_note_status(message.from_user.id)
    fragments_help = _fragments_help(message.from_user.id)
    help_text = f"""🔄 This bot converts:  
🎵 <b>MP3 audio files</b> → <i>Voice messages</i>  
🎬 <b>MP4 videos</b> → <i>Video notes</i>{note_status}
🎧 <b>Video notes</b> → <i>Voice messages</i>

📤 Just upload your file and pick an option you need.
ℹ️ <b>Note:</b> If you want to create a <b>video note</b>, the video must be shorter than ⏱️ <b>60 seconds</b>.
{fragments_help}

⚠️ <b>ATTENTION!</b> Audio and video files must be under <b>20 MB</b>! ⚠️
"""
    await message.answer(text=help_text,
                         parse_mode=ParseMode.HTML)
