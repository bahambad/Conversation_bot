import ffmpeg

from modules.errors import ProcessingError, VideoTooLongError
from modules.ffmpeg_runner import probe, run_ffmpeg

# Максимальная длительность кружка, секунд
MAX_NOTE_DURATION = 60


# Функция для обрезки видео в квадрат
async def crop_video_to_square(input_path, output_path) -> None:
    """
    Обрезает видео по центру до квадратной формы и уменьшает разрешение до 384x384.

    Raises:
        VideoTooLongError: видео длиннее MAX_NOTE_DURATION секунд.
        ProcessingError: в файле нет видеопотока или FFmpeg вернул ошибку.
    """
    info = await probe(input_path)

    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    if duration >= MAX_NOTE_DURATION:
        raise VideoTooLongError()

    video_stream = next((stream for stream in info.get('streams', []) if stream.get('codec_type') == 'video'), None)
    if video_stream is None:
        raise ProcessingError()

    width = int(video_stream['width'])
    height = int(video_stream['height'])
    min_dim = min(width, height)
    offset_x = (width - min_dim) // 2
    offset_y = (height - min_dim) // 2

    crop_filter = f"crop={min_dim}:{min_dim}:{offset_x}:{offset_y},scale=384:384"

    stream = ffmpeg.input(str(input_path)).output(
        str(output_path),
        vf=crop_filter,
        vcodec="libx264",
        acodec="aac",
        audio_bitrate="128k",
        format="mp4",
        movflags="faststart",
    )
    await run_ffmpeg(stream)
