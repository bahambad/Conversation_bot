import os

import ffmpeg


def is_number(n):
    try:
        int(n)
        return True
    except ValueError:
        return False

# Функция для добавления AVANGAARDD
async def avangard_video(input_path: str, output_path: str, audio_path: str, volume_parametr: int):
    """
    Добавляет к кружочку песенку AVANGARD.

    Args:
        input_path (str): Путь к входному видеофайлу.
        audio_path (str): Путь к добавляемому аудио.
        output_path (str): Путь для сохранения обработанного видеофайла.

    Raises:
        ffmpeg.Error: Если FFmpeg возвращает ошибку во время обработки.
    """
    # print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))


    try:
        print(f"Начало обработки: видео='{input_path}', аудио='{audio_path}', вывод='{output_path}'")

        # Определяем входные потоки
        input_video = ffmpeg.input(input_path)
        input_audio = ffmpeg.input(audio_path)

        # Выбираем нужные потоки: видео из первого файла, аудио из обоих
        video_stream = input_video['v']  # Видеопоток из input_path
        original_audio = input_video['a']  # Аудиопоток из input_path
        audio_bob = input_audio['a']  # Аудиопоток из audio_path


        volumek = volume_parametr / 500
        external_audio = ffmpeg.filter(audio_bob, 'volume', volume=volumek)

        # Смешиваем два аудиопотока с помощью фильтра 'amix'
        # inputs=2 указывает, что на вход фильтра подается 2 потока
        # duration='first' - альтернатива -shortest, выбирает длительность первого потока
        # normalize=True - (опционально) нормализует громкость, чтобы избежать клиппинга
        mixed_audio = ffmpeg.filter(
            [original_audio, external_audio],
            'amix',
            inputs=2,
            duration='shortest'
            # duration='first', # Можно использовать 'first', 'shortest', 'longest'
            # normalize=True   # Раскомментируйте для нормализации громкости
        )

        # Собираем команду для FFmpeg
        # Мы берем видеопоток video_stream и смешанный аудиопоток mixed_audio


        # stream = ffmpeg.output(
        #     video_stream,  # Видео (копируем без перекодирования для скорости)
        #     mixed_audio,  # Смешанный звук (будет перекодирован)
        #     output_path,
        #     vcodec='copy',  # Копировать видео кодек (быстрее, если не нужно менять формат)
        #     acodec='aac',  # Выбрать аудио кодек (AAC - хороший стандарт)
        #     audio_bitrate='128k',  # Установить битрейт аудио (например, 192 kbps)
        #     shortest=True
        #     # Опция "-shortest": завершить обработку, когда закончится самый короткий входной поток (в нашем случае - видео)
        # )

        # Используем явное указание аргумента filename:
        stream = ffmpeg.output(
            video_stream,
            mixed_audio,
            filename=output_path,  # <-- Явно указываем имя файла
            vcodec='copy',
            acodec='aac',
            audio_bitrate='128k',
            # shortest=True
        )


        # Запускаем процесс FFmpeg
        # overwrite_output=True позволяет перезаписать файл, если он уже существует
        print("Запуск команды FFmpeg...")
        stdout, stderr = stream.run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

        # Можно раскомментировать для отладки вывода FFmpeg
        # print("FFmpeg stdout:", stdout.decode())
        # print("FFmpeg stderr:", stderr.decode())
        print(f"Обработка успешно завершена. Результат сохранен в '{output_path}'")

    except ffmpeg.Error as e:
        print('Ошибка при обработке видео:', e)
        if e.stderr:
            print('FFmpeg stderr:', e.stderr.decode('utf8', errors='ignore'))
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути '{input_path}'")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")