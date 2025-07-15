# Функция для обрезки видео в квадрат
import os

import ffmpeg



# Функция для обрезки видео в квадрат
async def crop_video_to_square(input_path: str, output_path: str):
    """
    Обрезает видео по центру до квадратной формы и уменьшает разрешение до 384x384.

    Args:
        input_path (str): Путь к входному видеофайлу.
        output_path (str): Путь для сохранения обработанного видеофайла.
    """
    print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))

    try:
        probe = ffmpeg.probe(input_path)

        format_info = probe.get("format", {})
        duration = float(format_info.get("duration", 0))

        # Проверка на длительность
        if duration >= 60:
            print("❌ Видео слишком длинное:", duration, "секунд")
            return False


        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            print(f"Ошибка: Не найден видеопоток в файле '{input_path}'")
            return

        width = int(video_stream['width'])
        height = int(video_stream['height'])
        min_dim = min(width, height)
        offset_x = (width - min_dim) // 2
        offset_y = (height - min_dim) // 2

        crop_filter = f"crop={min_dim}:{min_dim}:{offset_x}:{offset_y},scale=384:384"

        (
            ffmpeg
            .input(input_path)
            .output(output_path,
                    vf=crop_filter,
                    vcodec="libx264",
                    acodec="aac",
                    audio_bitrate="128k",
                    format="mp4",
                    movflags="faststart")
            .run(overwrite_output=True)
        )

        print(f"Видео успешно обработано и сохранено в '{output_path}'")
        return True

    except ffmpeg.Error as e:
        print(f"Ошибка при обработке видео: {e.stderr.decode('utf8')}")
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути '{input_path}'")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")