"""Регистрация и активация аккаунта."""

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.core.forms import SignUpForm
from apps.users.models import UserProfile


def _send_activation_email(request: HttpRequest, user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = request.build_absolute_uri(
        f"/activate/{uid}/{token}/"
    )
    subject = "Подтвердите email в GitPlayground"
    text_body = render_to_string(
        "core/emails/activation_email.txt",
        {"user": user, "activation_url": activation_url},
    )
    send_mail(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("profile-self")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
        # public_nickname глобально уникален; чужой профиль мог занять строку, совпадающую с username.
        nickname = (user.username or "user")[:64]
        n = 0
        while UserProfile.objects.filter(public_nickname=nickname).exists():
            n += 1
            suffix = f"_{user.pk}_{n}"
            base = (user.username or "user")[: max(1, 64 - len(suffix))]
            nickname = (base + suffix)[:64]
        UserProfile.objects.create(user=user, public_nickname=nickname)
        _send_activation_email(request, user)
        return render(request, "core/signup_done.html", {"email": user.email})
    return render(request, "core/signup.html", {"form": form})


def activate_account(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (ValueError, TypeError, User.DoesNotExist):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "core/activation_invalid.html", status=400)
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    backend = settings.AUTHENTICATION_BACKENDS[0]
    login(request, user, backend=backend)
    return render(request, "core/activation_success.html")
