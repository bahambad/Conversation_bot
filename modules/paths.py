from pathlib import Path

# Пути считаются от корня проекта, а не от рабочей директории процесса
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
PICTURES_DIR = BASE_DIR / "pictures"
DOWNLOADS_DIR = BASE_DIR / "downloads"
