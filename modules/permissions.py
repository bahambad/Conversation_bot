from decouple import Csv, config

# Уровни доступа идут по возрастанию, и каждый следующий включает предыдущие:
#   все пользователи < привилегированные < пользователи LLM < админ
ADMIN_ID = int(config('ADMIN'))

# Привилегированные пользователи: им доступны функции, которые нельзя открыть всем
# из-за нагрузки на сервер или риска злоупотреблений (кружочки из видео, фрагменты по таймкодам).
# Один общий список на все такие функции, отдельные списки под каждую не заводятся.
# Задаётся в .env списком id через запятую: PRIVILEGED_USERS = 111,222
PRIVILEGED_USERS = frozenset(config('PRIVILEGED_USERS', default='', cast=Csv(int)))

# Пользователи LLM: им доступны функции, которые тратят платные токены языковой модели
# (сейчас это монтаж по текстовому запросу, /edit). Список намеренно отдельный и короткий:
# доступ к платным токенам — более высокий уровень доверия, чем доступ к кружочкам.
# Задаётся в .env так же: LLM_USERS = 111,222
LLM_USERS = frozenset(config('LLM_USERS', default='', cast=Csv(int)))


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def can_use_llm(user_id: int) -> bool:
    """Функции, расходующие платные токены модели: пользователи из LLM_USERS и админ."""
    return user_id in LLM_USERS or is_admin(user_id)


def is_privileged(user_id: int) -> bool:
    """Привилегированные функции: свой список плюс все, у кого уровень выше."""
    return user_id in PRIVILEGED_USERS or can_use_llm(user_id)


def can_use_fragments(user_id: int) -> bool:
    """Фрагменты по таймкодам — одна из привилегированных функций."""
    return is_privileged(user_id)
