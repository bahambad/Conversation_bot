import json
import logging

import aiohttp
from decouple import config

from modules.errors import UserFacingError

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = config('OPENROUTER_API_KEY', default='')
# Модель или пресет OpenRouter («@preset/имя»): модель меняется в интерфейсе OpenRouter без правок кода
LLM_MODEL = config('LLM_MODEL', default='')
# Необязательная более сильная модель: к ней бот обращается, только если основная не справилась
LLM_ESCALATION_MODEL = config('LLM_ESCALATION_MODEL', default='')

LLM_TIMEOUT = 90
LLM_MAX_TOKENS = 4000


class LLMError(UserFacingError):
    text = "⛔️ <b>The language model didn't answer.</b>\nPlease try again in a moment."


def is_configured() -> bool:
    return bool(OPENROUTER_API_KEY and LLM_MODEL)


async def ask_json(messages: list[dict], schema: dict, schema_name: str, model: str | None = None) -> dict:
    """
    Отправляет диалог модели и возвращает её ответ как JSON-объект заданной схемы.

    Raises:
        LLMError: сервис недоступен, вернул ошибку или ответ не является JSON.
    """
    payload = {
        "model": model or LLM_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    try:
        timeout = aiohttp.ClientTimeout(total=LLM_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload) as response:
                data = await response.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as e:
        logger.warning("LLM request failed: %s", e)
        raise LLMError() from e

    if not isinstance(data, dict) or "error" in data or not data.get("choices"):
        logger.warning("LLM returned an error: %s", str(data)[:500])
        raise LLMError()

    usage = data.get("usage") or {}
    logger.info("LLM answer from %s: %s input + %s output tokens, cost %s",
                data.get("model"), usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("cost"))

    content = (data["choices"][0].get("message") or {}).get("content") or ""
    try:
        result = json.loads(_strip_code_fence(content))
    except ValueError as e:
        logger.warning("LLM answer is not JSON: %s", content[:500])
        raise LLMError() from e
    if not isinstance(result, dict):
        raise LLMError()
    return result


def _strip_code_fence(text: str) -> str:
    """Некоторые модели оборачивают JSON в ```json ... ``` даже при заданном формате ответа."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()
