import ffmpeg

from modules.ffmpeg_runner import run_ffmpeg


def is_number(n):
    try:
        int(n)
        return True
    except ValueError:
        return False


# Функция для добавления AVANGAARDD
async def avangard_video(input_path, output_path, audio_path, volume_parametr: int) -> None:
    """
    Добавляет к кружочку песенку AVANGARD.

    Args:
        input_path: Путь к входному видеофайлу.
        output_path: Путь для сохранения обработанного видеофайла.
        audio_path: Путь к добавляемому аудио.
        volume_parametr: Громкость добавляемого аудио в процентах.

    Raises:
        ProcessingError: Если FFmpeg возвращает ошибку во время обработки.
    """
    input_video = ffmpeg.input(str(input_path))
    input_audio = ffmpeg.input(str(audio_path))

    video_stream = input_video['v']  # Видеопоток из input_path
    original_audio = input_video['a']  # Аудиопоток из input_path
    audio_bob = input_audio['a']  # Аудиопоток из audio_path

    volumek = volume_parametr / 500
    external_audio = ffmpeg.filter(audio_bob, 'volume', volume=volumek)

    # Смешиваем два аудиопотока; длительность — по самому короткому (то есть по видео)
    mixed_audio = ffmpeg.filter(
        [original_audio, external_audio],
        'amix',
        inputs=2,
        duration='shortest',
    )

    stream = ffmpeg.output(
        video_stream,
        mixed_audio,
        filename=str(output_path),
        vcodec='copy',  # Видео копируем без перекодирования
        acodec='aac',
        audio_bitrate='128k',
    )
    await run_ffmpeg(stream)
