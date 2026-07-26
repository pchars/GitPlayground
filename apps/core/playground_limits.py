"""Simple fixed-window rate limiting for playground API and auth (Django cache)."""

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
        "validate": int(os.getenv("PLAYGROUND_RL_MAX_VALIDATE", "60")),
    }
    return defaults.get(action, 120)


def _allow_key(key: str, *, window: int, cap: int) -> bool:
    now = int(time.time())
    slot = now // window
    full_key = f"{key}:{slot}"
    ttl = max(1, window - (now % window))
    if cache.add(full_key, 1, ttl):
        return True
    try:
        n = cache.incr(full_key)
    except ValueError:
        cache.set(full_key, 1, ttl)
        return True
    return n <= cap


def allow_playground_action(user_id: int, task_id: int, action: str) -> bool:
    """Return False when the limit for the current time window is exhausted."""
    window = _window_sec()
    cap = _cap_for(action)
    return _allow_key(f"gprl:v1:{user_id}:{task_id}:{action}", window=window, cap=cap)


def _auth_window_sec() -> int:
    return max(1, int(os.getenv("AUTH_RL_WINDOW_SEC", "60")))


def _auth_cap(action: str) -> int:
    defaults = {
        "login": int(os.getenv("AUTH_RL_MAX_LOGIN", "20")),
        "signup": int(os.getenv("AUTH_RL_MAX_SIGNUP", "10")),
        "password_reset": int(os.getenv("AUTH_RL_MAX_PASSWORD_RESET", "5")),
    }
    return defaults.get(action, 10)


def allow_auth_action(client_key: str, action: str) -> bool:
    """IP/client keyed limit for auth POSTs."""
    safe = (client_key or "unknown").replace(" ", "")[:128]
    return _allow_key(
        f"authrl:v1:{action}:{safe}",
        window=_auth_window_sec(),
        cap=_auth_cap(action),
    )


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.META.get("REMOTE_ADDR") or "unknown"
