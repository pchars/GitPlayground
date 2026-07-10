"""Automatic cache-busting for static files.

The ``static_v`` tag works like built-in ``static`` but appends a short content
hash to the URL (``?v=<hash>``). The hash is recomputed only when the file
changes (cache key: path + mtime), so browsers get fresh CSS/JS without manual
version bumps in templates.

Registered as a template builtin (see ``TEMPLATES`` in settings), so no
``{% load %}`` is required.
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
    """Absolute path to the source static file, or None."""
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
    """SHA-256 (first 8 hex chars) of file content; cached by mtime."""
    try:
        with open(source, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None
    return digest[:8]


@register.simple_tag
def static_v(path: str) -> str:
    """Return static URL with automatic ``?v=<hash>``."""
    url = static(path)
    source = _resolve_source_path(path)
    version = _content_hash(source, _current_mtime(source)) if source else None
    if not version:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"
