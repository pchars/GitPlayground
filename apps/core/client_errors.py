"""Stable, user-safe error copy for HTTP/JSON responses.

Internal exception text must be logged server-side only (CodeQL py/stack-trace-exposure).
"""

from __future__ import annotations

import logging

SANDBOX_UNAVAILABLE = "Песочница временно недоступна. Попробуйте позже."
FILE_READ_FAILED = "Не удалось прочитать файл."
FILE_WRITE_FAILED = "Не удалось записать файл."
FILE_EXISTS_READ_FAILED = "Не удалось прочитать существующий файл."
VALIDATION_INTERNAL_ERROR = "Ошибка проверки задачи."
INSUFFICIENT_HINT_POINTS = "Недостаточно баллов для покупки подсказки."
MKDIR_FAILED = "mkdir: не удалось создать каталог."


def log_exception(logger: logging.Logger, context: str, exc: BaseException) -> None:
    logger.exception("%s", context, exc_info=exc)
