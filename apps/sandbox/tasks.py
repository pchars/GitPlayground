from celery import shared_task
from django.utils import timezone

from apps.core.services.sandbox_ops import stop_session
from apps.sandbox.models import SandboxSession


@shared_task
def cleanup_expired_sandboxes() -> int:
    expired_sessions = SandboxSession.objects.filter(
        expires_at__lt=timezone.now(),
        status__in=[SandboxSession.Status.STARTING, SandboxSession.Status.ACTIVE],
    )
    cleaned = 0
    for session in expired_sessions:
        stop_session(session)
        session.status = SandboxSession.Status.EXPIRED
        session.save(update_fields=["status", "last_activity_at"])
        cleaned += 1
    return cleaned
