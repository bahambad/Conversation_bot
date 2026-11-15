"""
Экспериментальная функция: монтаж по текстовому запросу (/edit).

Доступна пользователям из LLM_USERS и админу, в сообщениях бота не упоминается. В сессии
монтажа пользователь присылает файлы и пишет обычным текстом, что с ними сделать; языковая модель
составляет команду ffmpeg, бот показывает план и после подтверждения выполняет его.
"""
import asyncio
import html
import re
import shlex
import shutil
from contextlib import suppress
from pathlib import Path

from aiogram import Bot, F, Router, types
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from yt_dlp.utils import sanitize_filename

from keyboards.edit_keyboard import EditCdData, EditLinkCdData, builder_edit_link_kb, builder_edit_plan_kb
from modules import llm
from modules.edit_engine import execute_plan, make_plan
from modules.edit_session import EditSession, LinkRequest, SessionFile, close_session, get_session, open_session
from modules.errors import UnsupportedUrlError
from modules.jobs import download_tg_file, heavy_job, is_busy, job_dir, report_errors
from modules.permissions import can_use_llm, is_admin
from modules.timecodes import find_time_range, format_timecode, parse_time_range
from modules.yt_downloads import (MAX_AUDIO_FRAGMENT_DURATION, MAX_FRAGMENT_DURATION, MAX_FRAGMENT_SIZE,
                                  download_media, validate_url)
from routers.video_processing import _extract_links
from states import Edit

router = Router(name=__name__)


def _has_access(event: types.Message | CallbackQuery) -> bool:
    return event.from_user is not None and can_use_llm(event.from_user.id)


# Всё в этом роутере — только для тех, кому разрешено тратить токены модели (LLM_USERS и админ).
# Для остальных команда /edit как будто не существует.
router.message.filter(_has_access)
router.callback_query.filter(_has_access)

START_TEXT = """🎛 <b>Editing session started.</b>

1. Send me audio or video files (a caption becomes the file's name) or a link to a video. \
A link can go with timecodes, for example <code>https://youtu.be/... 1:02:30-1:03:10</code>.
2. Tell me in plain words what to do with them, for example:
<i>put "intro" over the video starting at 0:15 at 30% volume</i>
3. I'll show the plan; press <b>Run</b> to execute it. The result joins the session files.

/files — list the files, /done — finish and delete them."""
NOT_CONFIGURED_TEXT = "⛔️ The language model is not configured: set OPENROUTER_API_KEY and LLM_MODEL in .env."
EXPIRED_TEXT = "⌛️ The editing session has expired. Send /edit to start a new one."
NO_FILES_TEXT = "📂 There are no files in the session yet. Send me audio, video or a link first."
NOT_MEDIA_TEXT = "⛔️ I can only work with audio and video files."
FULL_TEXT = "⛔️ The session is full. Send /done and start a new one with /edit."
OUTDATED_TEXT = "This plan is outdated."
BUSY_ALERT_TEXT = "⏳ Your previous request is still being processed. Please wait."
LINK_TEXT = "🔗 What should I add from this link?"
LINK_RANGE_TEXT = "🔗 Fragment {start}–{end}: add it as video or as audio?"
ASK_TIMECODES_TEXT = """✂️ Send the timecodes of the {kind} fragment: <code>start-end</code>

For example <code>1:02:30-1:03:10</code> or <code>90-150</code> (seconds).
The fragment can be up to {max_length} long.

Send /back to return to the session without adding anything."""
INVALID_TIMECODES_TEXT = """⛔️ I can't read these timecodes.
Send them as <code>start-end</code>, for example <code>1:02:30-1:03:10</code>, or /back."""
TOO_LONG_TEXT = "⛔️ The {kind} fragment can be up to {max_length} long."
# Время на скачивание по ссылке внутри сессии, секунд
LINK_TIMEOUT = 900

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
        # Подробности настройки — только админу
        text = NOT_CONFIGURED_TEXT if is_admin(message.from_user.id) else "⛔️ Editing is not available right now."
        await message.answer(text)
        return
    # Новая сессия заменяет прежнюю вместе с её файлами
    open_session(message.from_user.id)
    await state.set_state(Edit.active)
    await message.answer(START_TEXT, parse_mode=ParseMode.HTML)


@router.message(StateFilter(Edit), Command("done"))
async def finish_edit(message: types.Message, state: FSMContext):
    close_session(message.from_user.id)
    await state.clear()
    await message.answer("✅ The editing session is finished, its files are deleted.")


@router.message(StateFilter(Edit), Command("files"))
async def list_files(message: types.Message, state: FSMContext):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    if not session.files:
        await message.answer(NO_FILES_TEXT)
        return
    await message.answer("\n".join(_describe(file) for file in session.files), parse_mode=ParseMode.HTML)


@router.message(StateFilter(Edit), F.audio | F.voice | F.video | F.video_note | F.document)
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


def _max_duration(audio_only: bool) -> int:
    return MAX_AUDIO_FRAGMENT_DURATION if audio_only else MAX_FRAGMENT_DURATION


def _range_label(time_range: tuple[int, int]) -> str:
    return f"{format_timecode(time_range[0])}-{format_timecode(time_range[1])}"


async def _download_to_session(session: EditSession, url: str, audio_only: bool,
                               time_range: tuple[int, int] | None) -> SessionFile:
    """Скачивает запись или её фрагмент по ссылке и добавляет в файлы сессии."""
    with job_dir() as workdir:
        # yt-dlp блокирующий, поэтому выполняем его в отдельном потоке.
        # Файл не отправляется в Telegram, поэтому лимит — как у фрагментов, а не 20 МБ.
        media = await asyncio.to_thread(
            download_media, url, workdir, audio_only,
            max_size=MAX_FRAGMENT_SIZE, timeout=LINK_TIMEOUT, time_range=time_range,
        )
        name = (media.title or "video")[:40]
        if time_range is not None:
            name += " " + _range_label(time_range)
        path = session.new_path(media.path.suffix)
        shutil.move(media.path, path)
    try:
        return await session.add_file(path, name)
    except BaseException:
        with suppress(OSError):
            path.unlink()
        raise


async def _add_from_link(bot: Bot, chat_id: int, user_id: int, session: EditSession, url: str,
                         audio_only: bool, time_range: tuple[int, int] | None) -> bool:
    """Скачивает по ссылке с сообщениями о ходе работы. Возвращает True при успехе."""
    added = False
    async with report_errors(bot, chat_id):
        async with heavy_job(user_id):
            what = "audio" if audio_only else "video"
            if time_range is not None:
                what += " fragment " + _range_label(time_range)
            waiting_message = await bot.send_message(chat_id, f"⬇️ Downloading the {what}...")
            try:
                async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
                    file = await _download_to_session(session, url, audio_only, time_range)
            finally:
                with suppress(TelegramAPIError):
                    await waiting_message.delete()
            await bot.send_message(chat_id, "Added: " + _describe(file), parse_mode=ParseMode.HTML)
            added = True
    return added


# Ссылка в сессии: её содержимое становится файлом сессии, а не отправляется обратно в чат
@router.message(Edit.active, F.text, _extract_links)
async def handle_link(message: types.Message, state: FSMContext, links: list[str]):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    if session.is_full():
        await message.answer(FULL_TEXT)
        return

    url = None
    error = None
    for link in links:
        try:
            url = validate_url(link)
            break
        except UnsupportedUrlError as e:
            error = error or e
    if url is None:
        await message.answer(text=error.text, parse_mode=ParseMode.HTML)
        return

    # Таймкоды можно написать прямо рядом со ссылкой
    text = message.text
    for link in links:
        text = text.replace(link, " ")
    time_range = find_time_range(text)

    link_request = session.new_link(url, time_range)
    if time_range is None:
        text = LINK_TEXT
    else:
        text = LINK_RANGE_TEXT.format(start=format_timecode(time_range[0]), end=format_timecode(time_range[1]))
    await message.answer(text, reply_markup=builder_edit_link_kb(link_request.id, has_range=time_range is not None))


@router.callback_query(EditLinkCdData.filter())
async def handle_link_button(call: CallbackQuery, callback_data: EditLinkCdData, bot: Bot, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    session = get_session(user_id)
    link: LinkRequest | None = session.links.get(callback_data.link_id) if session else None

    async def remove_keyboard_message() -> None:
        with suppress(TelegramAPIError):
            await bot.delete_message(chat_id, call.message.message_id)

    if link is None:
        await call.answer(OUTDATED_TEXT, show_alert=True)
        await remove_keyboard_message()
        return
    audio_only = callback_data.audio
    max_length = _max_duration(audio_only)

    if callback_data.part and link.time_range is None:
        # Таймкоды ещё не указаны — спрашиваем их отдельным сообщением
        await call.answer()
        await remove_keyboard_message()
        await state.set_state(Edit.timecodes)
        await state.update_data(link_id=link.id, link_audio=audio_only)
        text = ASK_TIMECODES_TEXT.format(kind="audio" if audio_only else "video",
                                         max_length=format_timecode(max_length))
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        return

    time_range = link.time_range if callback_data.part else None
    if time_range is not None and time_range[1] - time_range[0] > max_length:
        await call.answer(TOO_LONG_TEXT.format(kind="audio" if audio_only else "video",
                                               max_length=format_timecode(max_length)), show_alert=True)
        return
    if is_busy(user_id):
        await call.answer(BUSY_ALERT_TEXT, show_alert=True)
        return

    await call.answer()
    await remove_keyboard_message()
    if await _add_from_link(bot, chat_id, user_id, session, link.url, audio_only, time_range):
        session.links.pop(link.id, None)


@router.message(Edit.timecodes, Command("back"))
async def back_to_session(message: types.Message, state: FSMContext):
    await state.set_state(Edit.active)
    await message.answer("↩️ Back to the editing session.")


@router.message(Edit.timecodes, F.text)
async def handle_link_timecodes(message: types.Message, state: FSMContext, bot: Bot):
    session = await _session_or_expire(message.from_user.id, state)
    if session is None:
        await message.answer(EXPIRED_TEXT)
        return
    data = await state.get_data()
    link = session.links.get(data.get("link_id"))
    audio_only = bool(data.get("link_audio"))
    if link is None:
        await state.set_state(Edit.active)
        await message.answer(OUTDATED_TEXT)
        return

    try:
        time_range = parse_time_range(message.text)
    except ValueError:
        await message.answer(INVALID_TIMECODES_TEXT, parse_mode=ParseMode.HTML)
        return
    if time_range[1] - time_range[0] > _max_duration(audio_only):
        await message.answer(TOO_LONG_TEXT.format(kind="audio" if audio_only else "video",
                                                  max_length=format_timecode(_max_duration(audio_only))))
        return

    # При ошибке остаёмся в ожидании таймкодов: можно прислать другие или выйти через /back
    if await _add_from_link(bot, message.chat.id, message.from_user.id, session, link.url, audio_only, time_range):
        session.links.pop(link.id, None)
        await state.set_state(Edit.active)


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
