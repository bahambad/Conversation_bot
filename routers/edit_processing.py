"""
Экспериментальная функция: монтаж по текстовому запросу (/edit).

Доступна только админу и нигде в сообщениях бота не упоминается. В сессии монтажа
админ присылает файлы и пишет обычным текстом, что с ними сделать; языковая модель
составляет команду ffmpeg, бот показывает план и после подтверждения выполняет его.
"""
import html
import re
import shlex
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from yt_dlp.utils import sanitize_filename

from keyboards.edit_keyboard import EditCdData, builder_edit_plan_kb
from modules import llm
from modules.edit_engine import execute_plan, make_plan
from modules.edit_session import EditSession, SessionFile, close_session, get_session, open_session
from modules.jobs import download_tg_file, heavy_job, is_busy, report_errors
from modules.permissions import ADMIN_ID
from modules.timecodes import format_timecode
from states import Edit

router = Router(name=__name__)
# Всё в этом роутере — только для админа
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)

START_TEXT = """🎛 <b>Editing session started.</b>

1. Send me audio or video files. A caption becomes the file's name.
2. Tell me in plain words what to do with them, for example:
<i>put "intro" over the video starting at 0:15 at 30% volume</i>
3. I'll show the plan; press <b>Run</b> to execute it. The result joins the session files.

/files — list the files, /done — finish and delete them."""
NOT_CONFIGURED_TEXT = "⛔️ The language model is not configured: set OPENROUTER_API_KEY and LLM_MODEL in .env."
EXPIRED_TEXT = "⌛️ The editing session has expired. Send /edit to start a new one."
NO_FILES_TEXT = "📂 There are no files in the session yet. Send me audio or video first."
NOT_MEDIA_TEXT = "⛔️ I can only work with audio and video files."
FULL_TEXT = "⛔️ The session is full. Send /done and start a new one with /edit."
OUTDATED_TEXT = "This plan is outdated."
BUSY_ALERT_TEXT = "⏳ Your previous request is still being processed. Please wait."

_SAFE_SUFFIX_RE = re.compile(r'^\.[A-Za-z0-9]{1,5}$')
# Расширение по умолчанию, если у файла из Telegram нет имени
_DEFAULT_SUFFIXES = {"audio": ".mp3", "voice": ".ogg", "video": ".mp4", "video_note": ".mp4", "document": ".bin"}
_DEFAULT_NAMES = {"voice": "voice message", "video_note": "video note"}


def _describe(file: SessionFile) -> str:
    icon = "🎬" if file.kind == "video" else "🎵"
    return f"{icon} <b>#{file.id}</b> {html.escape(file.name)} — {file.kind}, {format_timecode(round(file.duration))}"


async def _session_or_expire(event_user_id: int, state: FSMContext) -> EditSession | None:
    session = get_session(event_user_id)
    if session is None:
        await state.clear()
    return session


@router.message(Command("edit"))
async def start_edit(message: types.Message, state: FSMContext):
    if not llm.is_configured():
        await message.answer(NOT_CONFIGURED_TEXT)
        return
    # Новая сессия заменяет прежнюю вместе с её файлами
    open_session(message.from_user.id)
    await state.set_state(Edit.active)
    await message.answer(START_TEXT, parse_mode=ParseMode.HTML)


@router.message(Edit.active, Command("done"))
async def finish_edit(message: types.Message, state: FSMContext):
    close_session(message.from_user.id)
    await state.clear()
    await message.answer("✅ The editing session is finished, its files are deleted.")


@router.message(Edit.active, Command("files"))
async def list_files(message: types.Message, state: FSMContext):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    if not session.files:
        await message.answer(NO_FILES_TEXT)
        return
    await message.answer("\n".join(_describe(file) for file in session.files), parse_mode=ParseMode.HTML)


@router.message(Edit.active, F.audio | F.voice | F.video | F.video_note | F.document)
async def add_file(message: types.Message, state: FSMContext, bot: Bot):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    if session.is_full():
        await message.answer(FULL_TEXT)
        return

    kind = next(k for k in ("audio", "voice", "video", "video_note", "document") if getattr(message, k))
    media = getattr(message, kind)
    # Файлом без сжатия можно прислать что угодно; ffmpeg «прочитает» даже текст, поэтому смотрим на тип
    if kind == "document" and not (media.mime_type or "").startswith(("audio/", "video/")):
        await message.answer(NOT_MEDIA_TEXT)
        return
    original_name = getattr(media, "file_name", None) or ""
    suffix = Path(original_name).suffix
    if not _SAFE_SUFFIX_RE.match(suffix):
        suffix = _DEFAULT_SUFFIXES[kind]
    # Имя файла в сессии: подпись, иначе имя из Telegram, иначе тип сообщения
    name = message.caption or Path(original_name).stem or _DEFAULT_NAMES.get(kind, kind)

    async with report_errors(bot, message.chat.id):
        path = session.new_path(suffix.lower())
        try:
            await download_tg_file(bot, media.file_id, media.file_size, path)
            file = await session.add_file(path, name)
        except BaseException:
            with suppress(OSError):
                path.unlink()
            raise
        await message.answer("Added: " + _describe(file), parse_mode=ParseMode.HTML)


@router.message(Edit.active, F.text)
async def handle_request(message: types.Message, state: FSMContext, bot: Bot):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    if not session.files:
        await message.answer(NO_FILES_TEXT)
        return

    async with report_errors(bot, message.chat.id):
        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            status, text, plan = await make_plan(session, message.text)

        if plan is None:
            icon = "❓" if status == "clarify" else "⛔️"
            await message.answer(f"{icon} {html.escape(text)}", parse_mode=ParseMode.HTML)
            return

        # Саму команду показываем в сворачиваемой цитате — на случай, если захочется её проверить
        command = shlex.join(["ffmpeg", *plan.args])[:1500]
        await message.answer(
            f"📝 {html.escape(text)}\n\n<blockquote expandable>{html.escape(command)}</blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=builder_edit_plan_kb(plan.id),
        )


@router.callback_query(EditCdData.filter())
async def handle_plan_button(call: CallbackQuery, callback_data: EditCdData, bot: Bot, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    session = get_session(user_id)
    plan = session.pending if session else None

    async def remove_buttons() -> None:
        with suppress(TelegramAPIError):
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id,
                                                reply_markup=None)

    if plan is None or plan.id != callback_data.plan_id:
        await call.answer(OUTDATED_TEXT, show_alert=True)
        await remove_buttons()
        return
    if callback_data.action != "run":
        session.pending = None
        await call.answer("Cancelled")
        await remove_buttons()
        return
    if is_busy(user_id):
        await call.answer(BUSY_ALERT_TEXT, show_alert=True)
        return
    session.pending = None

    async with report_errors(bot, chat_id):
        async with heavy_job(user_id):
            await call.answer()
            await remove_buttons()
            waiting_message = await bot.send_message(chat_id, "⚙️ Working on it...")
            try:
                action = ChatAction.UPLOAD_VIDEO if plan.output_ext == "mp4" else ChatAction.UPLOAD_DOCUMENT
                async with ChatActionSender(bot=bot, chat_id=chat_id, action=action):
                    file = await execute_plan(session, plan)
                    await _send_result(bot, chat_id, file)
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()


async def _send_result(bot: Bot, chat_id: int, file: SessionFile) -> None:
    filename = (sanitize_filename(file.name)[:80] or "result") + file.path.suffix
    document = types.FSInputFile(path=file.path, filename=filename)
    caption = "Result: " + _describe(file)
    if file.path.suffix == ".mp4":
        await bot.send_video(chat_id, video=document, caption=caption, parse_mode=ParseMode.HTML)
    elif file.path.suffix in (".mp3", ".m4a"):
        await bot.send_audio(chat_id, audio=document, title=file.name, caption=caption, parse_mode=ParseMode.HTML)
    else:
        await bot.send_document(chat_id, document=document, caption=caption, parse_mode=ParseMode.HTML)
