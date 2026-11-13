import ffmpeg

from modules.ffmpeg_runner import run_ffmpeg

# Требования Telegram к обложке аудио: JPEG, не больше 320x320 и 200 КБ
COVER_SIZE = 320


async def make_audio_cover(input_path, output_path) -> None:
    """
    Делает из произвольной картинки обложку для аудио: обрезает по центру
    до квадрата и сохраняет как JPEG 320x320.

    Raises:
        ProcessingError: если FFmpeg не смог прочитать картинку.
    """
    stream = ffmpeg.input(str(input_path)).output(
        str(output_path),
        vf=f"crop='min(iw,ih)':'min(iw,ih)',scale={COVER_SIZE}:{COVER_SIZE}",
        vframes=1,
        format='image2',
        vcodec='mjpeg',
        **{'q:v': 4},
    )
    await run_ffmpeg(stream, timeout=30)
