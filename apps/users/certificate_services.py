"""Issue and email practice-completion certificates."""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.achievements.models import UserAchievement
from apps.users.certificate_pdf import CERTIFICATE_DISCLAIMER, build_certificate_pdf
from apps.users.models import CompletionCertificate
from apps.users.services import ensure_user_profile

logger = logging.getLogger(__name__)

_ELIGIBLE_SLUGS = frozenset({"git_master", "quiz_all_complete"})


def user_eligible_for_certificate(user: User) -> bool:
    awarded = set(
        UserAchievement.objects.filter(user=user, achievement__slug__in=_ELIGIBLE_SLUGS).values_list(
            "achievement__slug", flat=True
        )
    )
    return _ELIGIBLE_SLUGS <= awarded


def _new_verification_code() -> str:
    for _ in range(8):
        code = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
        if not CompletionCertificate.objects.filter(verification_code=code).exists():
            return code
    return secrets.token_hex(8)


def _site_base() -> str:
    return getattr(settings, "SITE_BASE_URL", "").rstrip("/") or "http://127.0.0.1:8000"


def issue_completion_certificate(user: User, *, send_email: bool = True) -> CompletionCertificate | None:
    """Create certificate once when eligible; optionally queue email on first issue."""
    if not user_eligible_for_certificate(user):
        return None
    existing = CompletionCertificate.objects.filter(user=user).first()
    if existing:
        return existing

    profile = ensure_user_profile(user)
    display_name = (profile.certificate_name or user.get_username())[:120]
    code = _new_verification_code()
    verify_url = f"{_site_base()}{reverse('certificate-verify', kwargs={'code': code})}"
    issued_at = timezone.now()
    pdf_bytes = build_certificate_pdf(
        display_name=display_name,
        issued_at=issued_at,
        verification_code=code,
        verify_url=verify_url,
    )
    with transaction.atomic():
        cert = CompletionCertificate(
            user=user,
            verification_code=code,
            display_name=display_name,
        )
        cert.pdf.save(
            f"certificate-{code}.pdf",
            ContentFile(pdf_bytes),
            save=False,
        )
        cert.save()

    if send_email:
        from apps.users.tasks import send_certificate_email

        try:
            send_certificate_email.delay(cert.id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to queue certificate email for user_id=%s", user.pk)
    return cert


def queue_certificate_email(cert: CompletionCertificate) -> None:
    from apps.users.tasks import send_certificate_email

    send_certificate_email.delay(cert.id)


def certificate_email_body(*, display_name: str, verify_url: str, profile_url: str) -> str:
    return (
        f"Здравствуйте, {display_name}!\n\n"
        "Поздравляем: вы завершили практические задачи и квиз на GitPlayground.\n"
        "Во вложении — сертификат о прохождении практики на платформе "
        "(это не диплом и не документ об образовании).\n\n"
        f"{CERTIFICATE_DISCLAIMER}\n\n"
        f"Проверить сертификат: {verify_url}\n"
        f"Профиль: {profile_url}\n"
    )
