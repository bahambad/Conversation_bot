import asyncio
import logging

import ffmpeg

from modules.errors import ProcessingError

logger = logging.getLogger(__name__)

# Максимальное время работы одного процесса FFmpeg, секунд
FFMPEG_TIMEOUT = 180


async def run_ffmpeg(stream, timeout: float = FFMPEG_TIMEOUT) -> None:
    """
    Запускает FFmpeg отдельным процессом, не блокируя event loop.

    Raises:
        ProcessingError: FFmpeg завершился с ошибкой или не уложился в timeout.
    """
    stream = stream.global_args('-nostdin', '-hide_banner', '-loglevel', 'error')
    cmd = ffmpeg.compile(stream, overwrite_output=True)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("FFmpeg timed out after %s seconds", timeout)
        raise ProcessingError("⛔️ <b>Processing took too long</b> and was cancelled.") from None
    finally:
        # Сюда попадаем и при таймауте, и при отмене задачи: процесс не должен остаться висеть
        if process.returncode is None:
            process.kill()
            await process.wait()

    if process.returncode != 0:
        logger.error("FFmpeg failed with code %s: %s",
                     process.returncode, stderr.decode('utf8', errors='ignore')[-2000:])
        raise ProcessingError()


async def probe(path) -> dict:
    """Читает метаданные файла через ffprobe в отдельном потоке."""
    try:
        return await asyncio.to_thread(ffmpeg.probe, str(path))
    except ffmpeg.Error as e:
        logger.error("ffprobe failed: %s", (e.stderr or b'').decode('utf8', errors='ignore')[-2000:])
        raise ProcessingError() from e


class FfmpegCommandError(ProcessingError):
    """Готовая команда ffmpeg завершилась с ошибкой; stderr нужен, чтобы её можно было исправить."""

    def __init__(self, stderr: str) -> None:
        super().__init__()
        self.stderr = stderr


async def run_ffmpeg_command(command: list[str], cwd, timeout: float = FFMPEG_TIMEOUT) -> None:
    """
    Запускает готовую команду ffmpeg (список аргументов, без shell) в папке cwd.

    Raises:
        FfmpegCommandError: ffmpeg завершился с ошибкой.
        ProcessingError: команда не уложилась в timeout.
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("FFmpeg timed out after %s seconds", timeout)
        raise ProcessingError("⛔️ <b>Processing took too long</b> and was cancelled.") from None
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()

    if process.returncode != 0:
        text = stderr.decode('utf8', errors='ignore')[-2000:]
        logger.warning("FFmpeg command failed with code %s: %s", process.returncode, text)
        raise FfmpegCommandError(text)
