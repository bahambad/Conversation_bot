from decouple import Csv, config

ADMIN_ID = int(config('ADMIN'))

# Привилегированные пользователи: им доступны функции, которые нельзя открыть всем
# из-за нагрузки на сервер или риска злоупотреблений (кружочки из видео, фрагменты по таймкодам).
# Один общий список на все такие функции, отдельные списки под каждую не заводятся.
# Задаётся в .env списком id через запятую: PRIVILEGED_USERS = 111,222
PRIVILEGED_USERS = frozenset(config('PRIVILEGED_USERS', default='', cast=Csv(int)))


def is_privileged(user_id: int) -> bool:
    return user_id in PRIVILEGED_USERS


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def can_use_fragments(user_id: int) -> bool:
    """Фрагменты по таймкодам доступны привилегированным пользователям; админу — всегда."""
    return is_privileged(user_id) or is_admin(user_id)
