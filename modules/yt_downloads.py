import logging
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp
from decouple import Csv, config
from yt_dlp.utils import sanitize_filename

from modules.errors import MediaDownloadError, MediaTooBigError, UnsupportedUrlError
from modules.jobs import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# Сайты, с которых разрешено скачивать (включая поддомены).
# Произвольные адреса запрещены, иначе через бота можно обращаться
# к внутренней сети сервера. Список переопределяется переменной ALLOWED_DOMAINS.
DEFAULT_ALLOWED_DOMAINS = (
    "youtube.com,youtu.be,tiktok.com,instagram.com,twitter.com,x.com,"
    "vk.com,vkvideo.ru,rutube.ru,soundcloud.com,vimeo.com,twitch.tv"
)
ALLOWED_DOMAINS = tuple(
    domain.strip().lower().lstrip(".")
    for domain in config("ALLOWED_DOMAINS", default=DEFAULT_ALLOWED_DOMAINS, cast=Csv())
    if domain.strip()
)

MAX_URL_LENGTH = 2048
# Общее время на скачивание одного файла, секунд
DOWNLOAD_TIMEOUT = 300
# Если сайт не сообщает размер файла, принимаем только короткие записи
MAX_DURATION_WITHOUT_SIZE = 600
# Битрейт MP3, в который конвертируется аудио, кбит/с
MP3_BITRATE = 192

VIDEO_FORMAT = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
AUDIO_FORMAT = 'bestaudio/best'


@dataclass
class DownloadedMedia:
    path: Path
    filename: str  # имя файла, которое увидит пользователь
    title: str | None


class _SizeLimitExceeded(Exception):
    pass


class _DeadlineExceeded(Exception):
    pass


def validate_url(text: str) -> str:
    """
    Проверяет, что текст — это одна https-ссылка на разрешённый сайт.

    Raises:
        UnsupportedUrlError: если ссылка не подходит.
    """
    url = text.strip()
    if len(url) > MAX_URL_LENGTH or any(char.isspace() for char in url):
        raise UnsupportedUrlError()

    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError:
        raise UnsupportedUrlError() from None

    if parts.scheme != "https" or not host or port not in (None, 443):
        raise UnsupportedUrlError()
    if parts.username is not None or parts.password is not None:
        raise UnsupportedUrlError()
    if not any(host == domain or host.endswith("." + domain) for domain in ALLOWED_DOMAINS):
        raise UnsupportedUrlError(
            "⛔️ <b>This site is not supported.</b>\n"
            "Supported sites: " + ", ".join(ALLOWED_DOMAINS)
        )
    return url


def _estimate_size(info: dict, audio_only: bool) -> float | None:
    """Оценивает размер итогового файла в байтах, None — если данных недостаточно."""
    duration = info.get('duration')

    total = 0.0
    for fmt in info.get('requested_formats') or [info]:
        size = fmt.get('filesize') or fmt.get('filesize_approx')
        if not size and fmt.get('tbr') and duration:
            size = fmt['tbr'] * 1000 / 8 * duration
        if not size:
            return None
        total += size

    if audio_only and duration:
        # Аудио перекодируется в MP3, который может оказаться больше исходника
        total = max(total, MP3_BITRATE * 1000 / 8 * duration)
    return total


def _check_info(info: dict | None, audio_only: bool, max_size: int) -> None:
    """Отклоняет плейлисты, трансляции и слишком большие файлы ещё до скачивания."""
    if not info:
        raise MediaDownloadError()
    if info.get('_type', 'video') != 'video' or 'entries' in info:
        raise UnsupportedUrlError("⛔️ <b>Playlists are not supported.</b>\nPlease send a link to a single video.")
    if info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming'):
        raise UnsupportedUrlError("⛔️ <b>Live streams are not supported.</b>")

    size = _estimate_size(info, audio_only)
    if size is not None:
        if size > max_size:
            raise MediaTooBigError()
        return

    # Размер неизвестен: длинные записи отклоняем сразу, а для остальных
    # реальный объём контролируется во время скачивания (см. progress_hook)
    duration = info.get('duration')
    if duration and duration > MAX_DURATION_WITHOUT_SIZE:
        raise MediaTooBigError()


def _find_result(workdir: Path, audio_only: bool) -> Path | None:
    files = [
        path for path in workdir.iterdir()
        if path.is_file() and path.suffix not in ('.part', '.ytdl')
    ]
    expected_suffix = '.mp3' if audio_only else '.mp4'
    preferred = [path for path in files if path.suffix == expected_suffix]
    candidates = preferred or ([] if audio_only else files)
    return max(candidates, key=lambda path: path.stat().st_size, default=None)


def download_media(url: str, workdir: Path, audio_only: bool,
                   max_size: int = MAX_FILE_SIZE,
                   timeout: float = DOWNLOAD_TIMEOUT) -> DownloadedMedia:
    """
    Скачивает видео (MP4) или аудио (MP3) по ссылке в папку workdir.

    Функция блокирующая — вызывать через asyncio.to_thread.

    Raises:
        UnsupportedUrlError: плейлист, трансляция или неподдерживаемая ссылка.
        MediaTooBigError: файл больше max_size.
        MediaDownloadError: скачать не удалось.
    """
    deadline = time.monotonic() + timeout
    downloaded: dict[str, int] = {}

    def progress_hook(status: dict) -> None:
        # Исключение из хука прерывает скачивание — так лимиты соблюдаются,
        # даже если сайт сообщил неверный размер или не сообщил его вовсе
        if time.monotonic() > deadline:
            raise _DeadlineExceeded()
        if status.get('status') in ('downloading', 'finished'):
            downloaded[status.get('filename') or ''] = status.get('downloaded_bytes') or 0
            if sum(downloaded.values()) > max_size:
                raise _SizeLimitExceeded()

    ydl_opts = {
        'format': AUDIO_FORMAT if audio_only else VIDEO_FORMAT,
        'outtmpl': str(workdir / '%(id)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,  # Только одно видео
        'playlist_items': '1',
        # Плейлисты не разворачиваем: получаем только заголовок и отклоняем
        'extract_flat': 'in_playlist',
        # Без generic-экстрактора yt-dlp не ходит по произвольным страницам
        'allowed_extractors': ['default', '-generic'],
        'socket_timeout': 15,
        'retries': 3,
        'cachedir': False,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'progress_hooks': [progress_hook],
    }
    if audio_only:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(MP3_BITRATE),
        }]
    else:
        ydl_opts['merge_output_format'] = 'mp4'  # Объединяет видео и аудио в MP4

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            _check_info(info, audio_only, max_size)
            ydl.extract_info(url, download=True)
    except _SizeLimitExceeded:
        raise MediaTooBigError() from None
    except _DeadlineExceeded:
        raise MediaDownloadError("⛔️ <b>The download took too long</b> and was cancelled.") from None
    except yt_dlp.utils.DownloadError as e:
        logger.warning("yt-dlp failed: %s", e)
        raise MediaDownloadError() from e

    result = _find_result(workdir, audio_only)
    if result is None:
        logger.error("yt-dlp finished without a result file")
        raise MediaDownloadError()
    if result.stat().st_size > max_size:
        raise MediaTooBigError()

    title = info.get('title')
    filename = sanitize_filename(title or info.get('id') or 'media', restricted=False)[:100]
    return DownloadedMedia(path=result, filename=f"{filename or 'media'}{result.suffix}", title=title)
