from decouple import Csv, config

ADMIN_ID = int(config('ADMIN'))

# Пользователи, которым разрешено превращать видео в кружочки (video notes).
# Задаётся в .env списком id через запятую: VIDEO_NOTE_USERS = 111,222
VIDEO_NOTE_USERS = frozenset(config('VIDEO_NOTE_USERS', default='', cast=Csv(int)))


def can_make_video_notes(user_id: int) -> bool:
    return user_id in VIDEO_NOTE_USERS


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID
