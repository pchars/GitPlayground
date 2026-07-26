"""User profile and related learning statistics."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.core.forms import ProfileEditForm
from apps.core.services import profile_learning_stats
from apps.users.services import ensure_user_profile


def _render_profile(request: HttpRequest, user) -> HttpResponse:
    from apps.users.certificate_services import user_eligible_for_certificate
    from apps.users.models import CompletionCertificate

    stats = profile_learning_stats(user)
    cert = CompletionCertificate.objects.filter(user=user).first()
    return render(
        request,
        "core/profile.html",
        {
            "profile_user": user,
            **stats,
            "completion_certificate": cert,
            "certificate_eligible": cert is not None or user_eligible_for_certificate(user),
        },
    )


@login_required
def profile_self(request: HttpRequest) -> HttpResponse:
    return _render_profile(request, request.user)


def public_profile(request: HttpRequest, username: str) -> HttpResponse:
    """Legacy URL — профиль доступен только владельцу."""
    if not request.user.is_authenticated or request.user.username != username:
        raise Http404
    return _render_profile(request, request.user)


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    profile = ensure_user_profile(request.user)
    form = ProfileEditForm(request.POST or None, user=request.user, profile=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль обновлён.")
        return redirect("profile-self")
    return render(request, "core/profile_edit.html", {"form": form, "profile": profile})
