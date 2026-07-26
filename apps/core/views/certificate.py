"""Certificate download, resend, and public verify views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.users.certificate_services import (
    issue_completion_certificate,
    queue_certificate_email,
    user_eligible_for_certificate,
)
from apps.users.models import CompletionCertificate


@login_required
@require_GET
def certificate_download(request: HttpRequest) -> HttpResponse:
    cert = CompletionCertificate.objects.filter(user=request.user).first()
    if cert is None or not cert.pdf:
        raise Http404
    with cert.pdf.open("rb") as handle:
        payload = handle.read()
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="gitplayground-certificate.pdf"'
    return response


@login_required
@require_POST
def certificate_resend(request: HttpRequest) -> HttpResponse:
    cert = CompletionCertificate.objects.filter(user=request.user).first()
    if cert is None:
        if not user_eligible_for_certificate(request.user):
            messages.error(request, "Сертификат ещё недоступен: завершите все задачи и квиз.")
            return redirect("profile-self")
        cert = issue_completion_certificate(request.user, send_email=True)
        if cert is None:
            messages.error(request, "Не удалось выпустить сертификат. Попробуйте позже.")
            return redirect("profile-self")
        messages.success(request, "Сертификат выпущен, письмо отправлено.")
        return redirect("profile-self")
    try:
        queue_certificate_email(cert)
        messages.success(request, "Письмо с сертификатом отправлено повторно.")
    except Exception:  # noqa: BLE001
        messages.error(request, "Не удалось отправить письмо. Попробуйте позже.")
    return redirect("profile-self")


@require_GET
def certificate_verify(request: HttpRequest, code: str) -> HttpResponse:
    cert = get_object_or_404(CompletionCertificate, verification_code=code)
    return render(request, "core/certificate_verify.html", {"certificate": cert})


@login_required
@require_GET
def certificate_info(request: HttpRequest) -> HttpResponse:
    from apps.users.certificate_pdf import CERTIFICATE_DISCLAIMER, CERTIFICATE_TITLE
    from apps.users.certificate_services import certificate_progress_for_user
    from apps.users.services import ensure_user_profile

    profile = ensure_user_profile(request.user)
    progress = certificate_progress_for_user(request.user)
    return render(
        request,
        "core/certificate_info.html",
        {
            "certificate_title": CERTIFICATE_TITLE,
            "certificate_disclaimer": CERTIFICATE_DISCLAIMER,
            "demo_name": profile.certificate_name or request.user.get_username(),
            **progress,
        },
    )
