"""Автоматический cache-busting для статики.

Тег ``static_v`` работает как встроенный ``static``, но добавляет к URL
короткий хэш содержимого файла (``?v=<hash>``). Хэш пересчитывается только
при изменении файла (ключ кэша — путь + mtime), поэтому браузер всегда
получает свежую версию CSS/JS без ручного бампа версии в шаблонах.

Тег подключён как builtin (см. ``TEMPLATES`` в settings), так что
``{% load %}`` в шаблонах не нужен.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


def _resolve_source_path(path: str) -> str | None:
    """Абсолютный путь к исходному статическому файлу или None."""
    found = finders.find(path)
    if found:
        return found if isinstance(found, str) else found[0]
    if settings.STATIC_ROOT:
        candidate = Path(settings.STATIC_ROOT) / path
        if candidate.exists():
            return str(candidate)
    return None


def _current_mtime(source: str | None) -> float:
    if not source:
        return 0.0
    try:
        return Path(source).stat().st_mtime
    except OSError:
        return 0.0


@lru_cache(maxsize=256)
def _content_hash(source: str, _mtime: float) -> str | None:
    """SHA-256 (первые 8 символов) содержимого файла; кэшируется по mtime."""
    try:
        with open(source, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None
    return digest[:8]


@register.simple_tag
def static_v(path: str) -> str:
    """Вернуть URL статики с автоматическим ``?v=<hash>``."""
    url = static(path)
    source = _resolve_source_path(path)
    version = _content_hash(source, _current_mtime(source)) if source else None
    if not version:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"
