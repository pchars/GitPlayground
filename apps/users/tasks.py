"""Celery tasks for users app (certificate email)."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_certificate_email(certificate_id: int) -> bool:
    from apps.users.certificate_services import certificate_email_body
    from apps.users.models import CompletionCertificate

    try:
        cert = CompletionCertificate.objects.select_related("user").get(pk=certificate_id)
    except CompletionCertificate.DoesNotExist:
        return False
    user = cert.user
    if not user.email:
        logger.warning("No email for certificate user_id=%s", user.pk)
        return False

    site = getattr(settings, "SITE_BASE_URL", "").rstrip("/") or "http://127.0.0.1:8000"
    verify_url = f"{site}{reverse('certificate-verify', kwargs={'code': cert.verification_code})}"
    profile_url = f"{site}{reverse('profile-self')}"
    body = certificate_email_body(
        display_name=cert.display_name,
        verify_url=verify_url,
        profile_url=profile_url,
    )
    message = EmailMessage(
        subject="Сертификат о прохождении практики GitPlayground",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    if cert.pdf:
        cert.pdf.open("rb")
        try:
            message.attach(
                "gitplayground-certificate.pdf",
                cert.pdf.read(),
                "application/pdf",
            )
        finally:
            cert.pdf.close()
    try:
        message.send(fail_silently=False)
    except Exception:  # noqa: BLE001
        logger.exception("Certificate email failed for certificate_id=%s", certificate_id)
        return False
    CompletionCertificate.objects.filter(pk=cert.pk).update(email_sent_at=timezone.now())
    return True
