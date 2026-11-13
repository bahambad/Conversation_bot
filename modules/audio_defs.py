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


# Функция для подготовки голосового сообщения
async def voice_from_media(input_path, output_path) -> None:
    """
    Перекодирует звук из аудио или видео в OGG/Opus — формат голосовых сообщений Telegram.

    Только для такого файла Telegram показывает длительность и рисует волну громкости;
    MP3, отправленный как голосовое, может отображаться пустым (0:00 и ровная линия).

    Raises:
        ProcessingError: если FFmpeg не смог обработать файл (например, в нём нет звука).
    """
    original_audio = ffmpeg.input(str(input_path))['a:0']
    stream = ffmpeg.output(
        original_audio,
        filename=str(output_path),
        format='ogg',
        acodec='libopus',
        audio_bitrate='64k',
        ac=1,  # голосовые сообщения — моно
        ar=48000,
        map_metadata=-1,  # теги и обложка исходного файла в голосовом не нужны
    )
    await run_ffmpeg(stream)
