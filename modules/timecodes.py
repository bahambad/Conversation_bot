import re

# Разделитель между началом и концом: дефис, тире или пробел
_RANGE_RE = re.compile(r'^\s*([\d:]+)\s*(?:[-–—]|\s)\s*([\d:]+)\s*$')


def parse_timecode(text: str) -> int:
    """
    Переводит таймкод в секунды. Допустимые форматы: 90, 1:30, 1:02:30.

    Raises:
        ValueError: если текст не является таймкодом.
    """
    parts = text.split(':')
    if not 1 <= len(parts) <= 3 or not all(part.isdigit() and len(part) <= 6 for part in parts):
        raise ValueError(f"bad timecode: {text!r}")

    numbers = [int(part) for part in parts]
    # В записи с двоеточиями минуты и секунды не могут быть больше 59
    if any(number > 59 for number in numbers[1:]):
        raise ValueError(f"bad timecode: {text!r}")

    seconds = 0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def parse_time_range(text: str) -> tuple[int, int]:
    """
    Разбирает отрезок вида «1:02:30-1:03:10» или «90 150» в пару (начало, конец) в секундах.

    Raises:
        ValueError: если формат неверный или конец не позже начала.
    """
    match = _RANGE_RE.match(text)
    if match is None:
        raise ValueError(f"bad time range: {text!r}")
    start, end = parse_timecode(match.group(1)), parse_timecode(match.group(2))
    if end <= start:
        raise ValueError("the end must be later than the start")
    return start, end


def format_timecode(seconds: int) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"
