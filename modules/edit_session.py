"""Сессии монтажа (/edit): набор именованных файлов пользователя и история его запросов."""
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from modules.errors import ProcessingError
from modules.ffmpeg_runner import probe
from modules.paths import DOWNLOADS_DIR

# Сессия без активности закрывается, а её файлы удаляются
SESSION_TTL = 3 * 3600
MAX_FILES = 30
MAX_NAME_LENGTH = 60
# Сколько предыдущих шагов показывать модели
HISTORY_LENGTH = 4


@dataclass
class SessionFile:
    id: int
    name: str
    path: Path
    kind: str  # 'audio' или 'video'
    duration: float
    has_audio: bool
    has_video: bool

    def describe(self) -> dict:
        """Описание файла для языковой модели."""
        return {
            "id": self.id, "name": self.name, "kind": self.kind,
            "duration": round(self.duration, 2), "has_audio": self.has_audio, "has_video": self.has_video,
        }


@dataclass
class Plan:
    """Команда, которую модель предложила, а пользователь ещё не подтвердил."""
    id: int
    request: str
    message: str
    args: list[str]
    output_ext: str
    output_name: str
    # Диалог с моделью: продолжается, если команду придётся исправлять
    messages: list[dict]


@dataclass
class EditSession:
    user_id: int
    directory: Path
    files: list[SessionFile] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    pending: Plan | None = None
    last_used: float = field(default_factory=time.monotonic)
    _next_file_id: int = 1
    _next_plan_id: int = 1

    def touch(self) -> None:
        self.last_used = time.monotonic()

    def new_path(self, suffix: str) -> Path:
        """Путь для нового файла сессии; номер резервируется сразу."""
        file_id = self._next_file_id
        self._next_file_id += 1
        return self.directory / f"{file_id}{suffix}"

    async def add_file(self, path: Path, name: str) -> SessionFile:
        """
        Регистрирует уже сохранённый файл: читает его длительность и дорожки.

        Raises:
            ProcessingError: файл не читается или в нём нет ни звука, ни видео.
        """
        info = await probe(path)
        streams = info.get('streams', [])
        has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
        # Обложка внутри аудиофайла формально тоже видеопоток, но видео она не является
        has_video = any(
            stream.get('codec_type') == 'video' and not (stream.get('disposition') or {}).get('attached_pic')
            for stream in streams
        )
        if not has_audio and not has_video:
            raise ProcessingError()
        try:
            duration = float(info.get('format', {}).get('duration', 0))
        except (TypeError, ValueError):
            duration = 0.0

        file = SessionFile(
            id=int(path.stem),
            name=_clean_name(name) or f"file {path.stem}",
            path=path,
            kind='video' if has_video else 'audio',
            duration=duration,
            has_audio=has_audio,
            has_video=has_video,
        )
        self.files.append(file)
        return file

    def new_plan(self, **kwargs) -> Plan:
        self.pending = Plan(id=self._next_plan_id, **kwargs)
        self._next_plan_id += 1
        return self.pending

    def remember(self, request: str, reply: str, result: SessionFile | None = None) -> None:
        self.history.append({
            "request": request, "reply": reply, "result_file_id": result.id if result else None,
        })
        del self.history[:-HISTORY_LENGTH]

    def is_full(self) -> bool:
        return len(self.files) >= MAX_FILES


def _clean_name(name: str) -> str:
    return " ".join(name.split())[:MAX_NAME_LENGTH]


_sessions: dict[int, EditSession] = {}


def open_session(user_id: int) -> EditSession:
    """Начинает новую сессию; прежняя сессия пользователя закрывается."""
    close_session(user_id)
    _purge_expired()
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    session = EditSession(user_id=user_id, directory=Path(tempfile.mkdtemp(prefix="edit_", dir=DOWNLOADS_DIR)))
    _sessions[user_id] = session
    return session


def get_session(user_id: int) -> EditSession | None:
    _purge_expired()
    session = _sessions.get(user_id)
    if session is not None:
        session.touch()
    return session


def close_session(user_id: int) -> bool:
    """Закрывает сессию и удаляет её файлы. Возвращает False, если сессии не было."""
    session = _sessions.pop(user_id, None)
    if session is None:
        return False
    shutil.rmtree(session.directory, ignore_errors=True)
    return True


def _purge_expired() -> None:
    now = time.monotonic()
    for user_id in [uid for uid, session in _sessions.items() if now - session.last_used > SESSION_TTL]:
        close_session(user_id)
