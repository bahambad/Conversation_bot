import time
import uuid
from typing import Dict, Generic, Optional, Tuple, TypeVar

T = TypeVar("T")


class TTLStore(Generic[T]):
    """
    Временное хранилище значений для inline-кнопок.

    В callback_data помещается только короткий ключ, само значение лежит здесь.
    Записи живут ttl секунд, а общее количество ограничено max_size, поэтому
    хранилище не растёт бесконечно, если пользователи не нажимают кнопки.
    """

    def __init__(self, ttl: float = 3600, max_size: int = 5000) -> None:
        self.ttl = ttl
        self.max_size = max_size
        # dict сохраняет порядок вставки, поэтому самые старые записи — в начале
        self._items: Dict[str, Tuple[float, T]] = {}

    def put(self, value: T) -> str:
        self._purge()
        key = uuid.uuid4().hex
        self._items[key] = (time.monotonic() + self.ttl, value)
        return key

    def get(self, key: str) -> Optional[T]:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at <= time.monotonic():
            del self._items[key]
            return None
        return value

    def pop(self, key: str) -> Optional[T]:
        value = self.get(key)
        self._items.pop(key, None)
        return value

    def __len__(self) -> int:
        return len(self._items)

    def _purge(self) -> None:
        now = time.monotonic()
        for key in list(self._items):
            expired = self._items[key][0] <= now
            if not expired and len(self._items) < self.max_size:
                break
            del self._items[key]
