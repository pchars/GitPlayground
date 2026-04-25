"""Простое ограничение частоты запросов к API плейграунда (фиксированное окно, django cache)."""

from __future__ import annotations

import os
import time

from django.core.cache import cache


def _window_sec() -> int:
    return max(1, int(os.getenv("PLAYGROUND_RL_WINDOW_SEC", "60")))


def _cap_for(action: str) -> int:
    defaults = {
        "run": int(os.getenv("PLAYGROUND_RL_MAX_RUN", "120")),
        "hint": int(os.getenv("PLAYGROUND_RL_MAX_HINT", "60")),
        "file_read": int(os.getenv("PLAYGROUND_RL_MAX_FILE", "60")),
        "file_write": int(os.getenv("PLAYGROUND_RL_MAX_FILE", "60")),
    }
    return defaults.get(action, 120)


def allow_playground_action(user_id: int, task_id: int, action: str) -> bool:
    """Возвращает False, если лимит за текущее окно времени исчерпан."""
    window = _window_sec()
    cap = _cap_for(action)
    now = int(time.time())
    slot = now // window
    key = f"gprl:v1:{user_id}:{task_id}:{action}:{slot}"
    ttl = max(1, window - (now % window))
    if cache.add(key, 1, ttl):
        return True
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, ttl)
        return True
    return n <= cap
