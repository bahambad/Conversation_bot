from decouple import Csv, config

ADMIN_ID = int(config('ADMIN'))

# Привилегированные пользователи: им доступны функции, которые нельзя открыть всем
# из-за нагрузки на сервер или риска злоупотреблений (сейчас это кружочки из видео).
# Один общий список на все такие функции, отдельные списки под каждую не заводятся.
# Задаётся в .env списком id через запятую: PRIVILEGED_USERS = 111,222
PRIVILEGED_USERS = frozenset(config('PRIVILEGED_USERS', default='', cast=Csv(int)))


def is_privileged(user_id: int) -> bool:
    return user_id in PRIVILEGED_USERS


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID
