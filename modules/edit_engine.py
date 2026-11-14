"""
Монтаж по текстовому запросу: модель составляет команду ffmpeg, бот её проверяет и выполняет.

Здесь нет ничего про Telegram — только сессия, модель и ffmpeg.
"""
import json
import logging
from contextlib import suppress

from modules import llm
from modules.edit_command import MAX_OUTPUT_SIZE, CommandRejected, build_command
from modules.edit_prompt import ANSWER_SCHEMA, SYSTEM_PROMPT, build_fix_message, build_request_message
from modules.edit_session import EditSession, Plan, SessionFile
from modules.errors import UserFacingError
from modules.ffmpeg_runner import FfmpegCommandError, run_ffmpeg_command

logger = logging.getLogger(__name__)

SCHEMA_NAME = "edit_command"
# Сколько раз модель может исправить команду, не прошедшую проверку, и команду, упавшую в ffmpeg
MAX_VALIDATION_FIXES = 1
MAX_RUN_FIXES = 2
EDIT_FFMPEG_TIMEOUT = 300


class EditFailed(UserFacingError):
    text = "⛔️ <b>I couldn't build a working command for this request.</b>\nTry to rephrase it or split it into steps."


class ResultTooBig(UserFacingError):
    text = "⛔️ <b>The result is too big to send</b> (over 49 MB).\nTry a shorter fragment or an audio-only result."


def _inputs(session: EditSession) -> dict:
    return {file.id: file.path for file in session.files}


def _assistant(answer: dict) -> dict:
    return {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}


async def make_plan(session: EditSession, request: str, model: str | None = None) -> tuple[str, str, Plan | None]:
    """
    Спрашивает у модели, как выполнить запрос.

    Возвращает (статус, текст для пользователя, план). План есть только при статусе "ok";
    при "clarify" и "impossible" текст — это вопрос или объяснение модели.

    Raises:
        LLMError: модель недоступна.
        EditFailed: модель не смогла составить команду, проходящую проверку.
    """
    files = [file.describe() for file in session.files]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_request_message(files, session.history, request)},
    ]
    answer = await llm.ask_json(messages, ANSWER_SCHEMA, SCHEMA_NAME, model)

    for attempt in range(MAX_VALIDATION_FIXES + 1):
        status = answer.get("status")
        message = str(answer.get("message") or "").strip()
        if status != "ok":
            if status not in ("clarify", "impossible") or not message:
                raise EditFailed()
            session.remember(request, message)
            return status, message, None
        try:
            # Проверяем сразу, чтобы не показывать пользователю план, который нельзя выполнить
            build_command(answer.get("args"), _inputs(session), session.directory / "check")
            break
        except CommandRejected as e:
            logger.info("LLM command rejected: %s", e)
            if attempt == MAX_VALIDATION_FIXES:
                raise EditFailed() from e
            messages += [_assistant(answer), {"role": "user", "content": build_fix_message(str(e))}]
            answer = await llm.ask_json(messages, ANSWER_SCHEMA, SCHEMA_NAME, model)

    plan = session.new_plan(
        request=request,
        message=message,
        args=answer["args"],
        output_ext=str(answer.get("output_ext") or "mp3"),
        output_name=str(answer.get("output_name") or "").strip() or "result",
        messages=messages + [_assistant(answer)],
    )
    return "ok", message, plan


async def execute_plan(session: EditSession, plan: Plan, model: str | None = None) -> SessionFile:
    """
    Выполняет подтверждённый план. Если ffmpeg падает, его ошибка возвращается модели,
    и она исправляет команду (до MAX_RUN_FIXES раз). Результат добавляется в файлы сессии.

    Raises:
        EditFailed: рабочую команду получить не удалось.
        ResultTooBig: результат больше лимита на отправку.
        LLMError: модель недоступна.
    """
    args = plan.args
    messages = list(plan.messages)
    output = session.new_path("." + plan.output_ext)

    for attempt in range(MAX_RUN_FIXES + 1):
        try:
            command = build_command(args, _inputs(session), output)
            await run_ffmpeg_command(command, cwd=session.directory, timeout=EDIT_FFMPEG_TIMEOUT)
            if not output.is_file() or output.stat().st_size == 0:
                raise FfmpegCommandError("ffmpeg finished without errors but produced an empty output file")
            break
        except (FfmpegCommandError, CommandRejected) as e:
            with suppress(OSError):
                output.unlink()
            if attempt == MAX_RUN_FIXES:
                raise EditFailed() from e
            error = e.stderr if isinstance(e, FfmpegCommandError) else str(e)
            # Пути на сервере модели знать незачем
            error = error.replace(str(session.directory) + "/", "")
            # На последней попытке подключаем более сильную модель, если она задана
            fix_model = model
            if attempt == MAX_RUN_FIXES - 1 and llm.LLM_ESCALATION_MODEL:
                fix_model = llm.LLM_ESCALATION_MODEL
            messages.append({"role": "user", "content": build_fix_message(error)})
            answer = await llm.ask_json(messages, ANSWER_SCHEMA, SCHEMA_NAME, fix_model)
            if answer.get("status") != "ok" or not answer.get("args"):
                raise EditFailed() from e
            messages.append(_assistant(answer))
            args = answer["args"]
        except BaseException:
            # Таймаут, отмена задачи и прочее: недописанный файл в сессии не оставляем
            with suppress(OSError):
                output.unlink()
            raise

    if output.stat().st_size > MAX_OUTPUT_SIZE:
        output.unlink()
        raise ResultTooBig()

    file = await session.add_file(output, plan.output_name)
    session.remember(plan.request, plan.message, file)
    return file
