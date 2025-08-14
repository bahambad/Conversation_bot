import yt_dlp

#Функция скачивания видео с ютуба
def download_video_from_youtube(url):
    output_path = "downloads"
    downloaded_files = []

    def record_filename(info):
        """Функция, которая сохраняет путь к скачанному файлу."""
        filepath = info.get("filename")
        if filepath:
            downloaded_files.append(filepath)

    try:
        ydlp_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl':f'{output_path}/%(title)s.%(ext)s',
            'noplaylist':True, #Только одно видео
            'progress_hooks': [record_filename],  # Хук для сохранения пути
        }



        print(f'Attending to download: {url}')
        with yt_dlp.YoutubeDL(ydlp_opts) as ydl:
            ydl.download([url])
        print(downloaded_files)
        part_outpath = downloaded_files[0][:-4]
        # if part_outpath[-1] == '.':
        #     while part_outpath[-1] == '.':
        #         part_outpath = part_outpath[:-1]
        full_outpath = part_outpath + ".mp4"
        print(f'Success! Downloaded to {full_outpath}')
        return full_outpath


    except Exception as e:
        print(f"Ошибка! {str(e)}")
        return False





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
        full_outpath = downloaded_files[0][:-4] + ".mp3"
        print(f'Success! Downloaded to {full_outpath}')
        return full_outpath


    except Exception as e:
        print(f"Ошибка3! {str(e)}")
        return False


#Проверка размера видео
def check_video_size(url,max_limit_qual,  max_size_mb=20):
    ydl_opts = {
        'format': f'bestvideo[height<={max_limit_qual}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,  # не выводить лишние сообщения
        'no_warnings': True,  # отключить предупреждения
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Получаем размер в байтах (если доступен)
            filesize = info.get('filesize') or info.get('filesize_approx')

            if filesize is None:
                print("Не удалось определить размер видео.")
                return False

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
