import os

import ffmpeg


# Функция для вытаскивания аудио из видео
async def audio_from_video(input_path: str, output_path: str):
    # print("input_path:", input_path)
    print("exists:", os.path.exists(input_path))


    try:
        print(f"Начало обработки: видео='{input_path}', вывод='{output_path}'")

        # Определяем входные потоки
        input_video = ffmpeg.input(input_path)

        # Выбираем нужные потоки: видео из первого файла, аудио
        video_stream = input_video['v']  # Видеопоток из input_path
        original_audio = input_video['a']  # Аудиопоток из input_path




        # Используем явное указание аргумента filename:
        stream = ffmpeg.output(

            original_audio,
            filename=output_path,  # <-- Явно указываем имя файла
            acodec='libmp3lame',
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