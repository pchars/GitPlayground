"""HTTP-представления core-приложения (точка входа для urls)."""

from .auth import activate_account, signup_view
from .leaderboard import leaderboard
from .learning import tasks_list, theory_detail
from .pages import healthcheck, landing
from .playground import (
    playground,
    playground_hint,
    playground_log,
    playground_log_stream,
    playground_read_file,
    playground_reset,
    playground_run_command,
    playground_start,
    playground_stop,
    playground_validate,
    playground_write_file,
)
from .profile import profile_self, public_profile

__all__ = [
    "activate_account",
    "healthcheck",
    "landing",
    "leaderboard",
    "playground",
    "playground_hint",
    "playground_log",
    "playground_log_stream",
    "playground_read_file",
    "playground_reset",
    "playground_run_command",
    "playground_start",
    "playground_stop",
    "playground_validate",
    "playground_write_file",
    "profile_self",
    "public_profile",
    "signup_view",
    "tasks_list",
    "theory_detail",
]
