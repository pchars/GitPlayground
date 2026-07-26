"""Core HTTP views (entry point for URL routing)."""

from .auth import activate_account, signup_view
from .leaderboard import leaderboard
from .learning import tasks_list, theory_detail, theory_home
from .pages import healthcheck, landing
from .playground import (
    playground,
    playground_hint,
    playground_read_file,
    playground_reset,
    playground_run_command,
    playground_validate,
    playground_write_file,
)
from .legal import marketing_consent_info, privacy_policy, support_donate
from .certificate import certificate_download, certificate_resend, certificate_verify
from .profile import profile_edit, profile_self, public_profile

__all__ = [
    "activate_account",
    "certificate_download",
    "certificate_resend",
    "certificate_verify",
    "healthcheck",
    "landing",
    "leaderboard",
    "playground",
    "playground_hint",
    "playground_read_file",
    "playground_reset",
    "playground_run_command",
    "playground_validate",
    "playground_write_file",
    "profile_edit",
    "privacy_policy",
    "marketing_consent_info",
    "support_donate",
    "profile_self",
    "public_profile",
    "signup_view",
    "tasks_list",
    "theory_detail",
    "theory_home",
]
