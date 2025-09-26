import yt_dlp

#Функция скачивания видео с ютуба
def download_video_from_youtube(url):
    output_path = "downloads"
    downloaded_files = []

    def record_filename(info):
        """Функция, которая сохраняет путь к скачанному файлу."""
        filepath = info.get("filename")
        if info.get("status") == "finished":
            downloaded_files.append(filepath)

    try:
        ydlp_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl':f'{output_path}/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',  # Объединяет видео и аудио в MP4
            'noplaylist': True,  # Только одно видео
            'progress_hooks': [record_filename],  # Хук для сохранения пути
        }

        print(f'Attending to download: {url}')
        with yt_dlp.YoutubeDL(ydlp_opts) as ydl:
            ydl.download([url])
        print(downloaded_files)
        full_outpath = downloaded_files[0]
        final_outpath = full_outpath
        if '.f136' in full_outpath or '.webm' in full_outpath or '.m4a' in full_outpath:
            final_outpath = final_outpath.replace('.f136', '')
            final_outpath = final_outpath.replace('.webm', '.mp4')
            final_outpath = final_outpath.replace('.m4a', '.mp4')
        # [:-8] + "mp4"
        print(f'Success! Downloaded to {final_outpath}')
        return final_outpath


    except Exception as e:
        print(f"Ошибка! {str(e)}")




#Функция скачивания аудио из видео ютуба
def download_audio_from_youtube(url):
    output_path = "downloads"
    downloaded_files = []

    def hook(d):
        if d['status'] == 'finished':
            downloaded_files.append(d['filename'])

    try:
        ydlp_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'progress_hooks': [hook],
        }


        print(f'Attending to download: {url}')
        with yt_dlp.YoutubeDL(ydlp_opts) as ydl:
            ydl.download([url])
        # full_outpath = downloaded_files[0][:-4] + ".mp3"
        full_outpath = downloaded_files[0]
        final_outpath = full_outpath
        if '.f136' in full_outpath or '.webm' in full_outpath or '.m4a' in full_outpath:
            final_outpath = final_outpath.replace('.f136', '')
            final_outpath = final_outpath.replace('.webm', '.mp3')
            final_outpath = final_outpath.replace('.m4a', '.mp3')
        final_outpath = final_outpath[:-4] + ".mp3"
        print(f'Success! Downloaded to {full_outpath}')
        return final_outpath


    except Exception as e:
        print(f"Ошибка3! {str(e)}")
        return False


#Проверка размера видео
def check_video_size(url,max_limit_qual,is_audio,  max_size_mb=20):
    format_text = f'bestvideo[height<={max_limit_qual}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    if is_audio:
        format_text = 'bestaudio/best'
    ydl_opts = {
        'format': format_text,
        'quiet': True,  # не выводить лишние сообщения
        'no_warnings': True,  # отключить предупреждения
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Получаем размер в байтах (если доступен)
            filesize = info.get('filesize') or info.get('filesize_approx')
            video_duration = info.get('duration', 0)

            if filesize is None:
                # print("Не удалось определить размер видео.")
                # return False
                filesize = video_duration * 204800 / 8 #128*1000*1.6 Почему-то настоящий размер всегда больше в 1.5 поэтому я умножаю на 1.6 на запас

            filesize_mb = filesize / (1024 * 1024)  # Переводим в мегабайты

            if filesize_mb > max_size_mb:
                print(f"Видео слишком большое: {filesize_mb:.2f} MB (максимум {max_size_mb} MB)")
                return False
            else:
                print(f"Размер видео в порядке: {filesize_mb:.2f} MB")
                return True
    except Exception as e:
        print(f"Ошибка! {str(e)}")
        return False
