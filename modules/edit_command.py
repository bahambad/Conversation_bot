"""
Проверка команды ffmpeg, которую составила языковая модель, перед запуском.

Модели нельзя доверять: она может ошибиться или получить запрос, написанный с умыслом.
Поэтому разрешены только известные опции, входами могут быть только файлы сессии,
а всё похожее на пути, адреса и фильтры, работающие с файлами, отклоняется.
"""
import re
from pathlib import Path

OUTPUT_PLACEHOLDER = "{out}"
_INPUT_PLACEHOLDER_RE = re.compile(r'^\{(\d+)\}$')
_OPTION_RE = re.compile(r'^-([A-Za-z_][A-Za-z0-9_]*)((?::[A-Za-z0-9#]+)*)$')

MAX_ARGS = 200
MAX_ARG_LENGTH = 6000
# Результат больше не нужен: Telegram не даст боту отправить файл крупнее 50 МБ
MAX_OUTPUT_SIZE = 49 * 1024 * 1024

# Опции с одним значением
_VALUE_OPTIONS = frozenset({
    'i', 'ss', 'sseof', 'to', 't', 'itsoffset', 'stream_loop',
    'filter_complex', 'lavfi', 'filter', 'af', 'vf',
    'map', 'map_metadata', 'map_chapters', 'metadata', 'disposition',
    'c', 'codec', 'acodec', 'vcodec', 'b', 'ab', 'q', 'qscale', 'ar', 'ac', 'r', 's', 'aspect',
    'crf', 'preset', 'tune', 'profile', 'level', 'pix_fmt', 'g', 'bf', 'fps_mode', 'vsync',
    'movflags', 'frames', 'vframes', 'aframes', 'f', 'id3v2_version', 'write_xing',
    'compression_level', 'max_muxing_queue_size', 'avoid_negative_ts', 'fflags', 'async',
})
# Опции-флаги без значения
_FLAG_OPTIONS = frozenset({
    'shortest', 'vn', 'an', 'sn', 'dn', 'copyts', 'start_at_zero', 'accurate_seek', 'ignore_unknown',
})
# Форматы, которые можно указать через -f
_FORMATS = frozenset({'mp3', 'mp4', 'ipod', 'mov', 'ogg', 'opus', 'wav', 'flac', 'adts', 'matroska', 'webm'})

# Пути и адреса: «/» в начале значения или после разделителя, «..», «~», схемы протоколов.
# Деление в выражениях фильтров («iw/2», «1/3») под это не попадает.
_PATH_RE = re.compile(r'''(^|[=:'"\s,;|\[\]])[/\\~]|\.\.|\w+://''')
_PROTOCOL_RE = re.compile(
    r'\b(file|pipe|concat|concatf|subfile|data|crypto|cache|fd|tee|tcp|udp|tls|http|https|ftp|sftp|rtmp|rtp|rtsp|srt|unix|hls)\s*:',
    re.IGNORECASE,
)
# Фильтры, которые читают или пишут файлы, ходят в сеть или загружают внешний код
_FORBIDDEN_FILTERS = (
    'movie', 'amovie', 'subtitles', 'ass', 'sendcmd', 'asendcmd', 'zmq', 'azmq', 'ladspa', 'lv2',
    'frei0r', 'frei0r_src', 'sofalizer', 'arnndn', 'lut3d', 'lut1d', 'removelogo', 'cover_rect',
    'find_rect', 'signature', 'libvmaf', 'psnr', 'ssim', 'vidstabdetect', 'vidstabtransform',
    'metadata', 'ametadata', 'ocr', 'drawtext', 'afir', 'haldclutsrc', 'openclsrc', 'program_opencl',
)
_FORBIDDEN_FILTER_RE = re.compile(
    r'(^|[;,\]])\s*(' + '|'.join(_FORBIDDEN_FILTERS) + r'|dnn_\w+)\s*(=|@|\[|,|;|$)',
    re.IGNORECASE,
)
_FILTER_OPTIONS = frozenset({'filter_complex', 'lavfi', 'filter', 'af', 'vf'})


class CommandRejected(Exception):
    """Команда модели не прошла проверку. Текст ошибки возвращается модели для исправления."""


def build_command(args: list[str], inputs: dict[int, Path], output: Path) -> list[str]:
    """
    Проверяет аргументы от модели и превращает их в готовую команду ffmpeg.

    Args:
        args: аргументы без «ffmpeg»; входы обозначены как {id}, выход — как {out}.
        inputs: файлы сессии по их номерам.
        output: куда записать результат.

    Raises:
        CommandRejected: команда нарушает правила.
    """
    if not isinstance(args, list) or not args or not all(isinstance(arg, str) for arg in args):
        raise CommandRejected("args must be a non-empty array of strings")
    if len(args) > MAX_ARGS or any(len(arg) > MAX_ARG_LENGTH for arg in args):
        raise CommandRejected("the command is too long")
    if args[-1] != OUTPUT_PLACEHOLDER or args.count(OUTPUT_PLACEHOLDER) != 1:
        raise CommandRejected("{out} must appear exactly once, as the last argument")

    command = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y']
    used_inputs = 0
    position = 0
    body = args[:-1]
    while position < len(body):
        arg = body[position]
        match = _OPTION_RE.match(arg)
        if match is None:
            raise CommandRejected(f"unexpected argument {arg!r}: only options and the final {{out}} are allowed")
        name = match.group(1)

        if name in _FLAG_OPTIONS:
            command.append(arg)
            position += 1
            continue
        if name not in _VALUE_OPTIONS:
            raise CommandRejected(f"option {arg!r} is not allowed")
        if position + 1 >= len(body):
            raise CommandRejected(f"option {arg!r} needs a value")
        value = body[position + 1]
        position += 2

        if name == 'i':
            placeholder = _INPUT_PLACEHOLDER_RE.match(value)
            if placeholder is None or int(placeholder.group(1)) not in inputs:
                raise CommandRejected(f"-i must be followed by a placeholder of an existing file, got {value!r}")
            # Входы — только локальные файлы: вложенные ссылки внутри файла ffmpeg открывать не будет
            command += ['-protocol_whitelist', 'file', '-i', str(inputs[int(placeholder.group(1))])]
            used_inputs += 1
            continue

        _check_value(name, value)
        command += [arg, value]

    if used_inputs == 0:
        raise CommandRejected("the command has no inputs")

    # Страховка от бесконечного или огромного результата
    command += ['-fs', str(MAX_OUTPUT_SIZE + 1024 * 1024), str(output)]
    return command


def _check_value(option: str, value: str) -> None:
    if '{' in value or '}' in value:
        raise CommandRejected(f"placeholders are only allowed after -i and as the output, got {value!r}")
    if '\x00' in value or '\n' in value or '\r' in value:
        raise CommandRejected("control characters are not allowed")
    if option != 'metadata' and (_PATH_RE.search(value) or _PROTOCOL_RE.search(value)):
        raise CommandRejected(f"file paths, URLs and protocols are not allowed, got {value!r}")
    if option == 'f' and value not in _FORMATS:
        raise CommandRejected(f"format {value!r} is not allowed")
    if option in _FILTER_OPTIONS:
        forbidden = _FORBIDDEN_FILTER_RE.search(value)
        if forbidden:
            raise CommandRejected(f"filter {forbidden.group(2)!r} is not allowed")
