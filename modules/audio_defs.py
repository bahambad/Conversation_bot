import ffmpeg

from modules.ffmpeg_runner import run_ffmpeg


# Функция для вытаскивания аудио из видео
async def audio_from_video(input_path, output_path) -> None:
    """
    Извлекает аудиодорожку из видео в MP3.

    Raises:
        ProcessingError: если FFmpeg не смог обработать файл (например, в видео нет звука).
    """
    original_audio = ffmpeg.input(str(input_path))['a']
    stream = ffmpeg.output(
        original_audio,
        filename=str(output_path),
        acodec='libmp3lame',
        audio_bitrate='128k',
    )
    await run_ffmpeg(stream)
