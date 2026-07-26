"""Rate-limited auth views (login / password reset)."""

from __future__ import annotations

from django.contrib.auth.views import LoginView, PasswordResetView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.core.forms import LoginForm
from apps.core.playground_limits import allow_auth_action, client_ip

_AUTH_RATE_LIMIT_MESSAGE = "Слишком много попыток. Подождите немного и попробуйте снова."


class RateLimitedLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = LoginForm

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not allow_auth_action(client_ip(request), "login"):
            form = self.get_form()
            form.add_error(None, _AUTH_RATE_LIMIT_MESSAGE)
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)


class RateLimitedPasswordResetView(PasswordResetView):
    template_name = "core/password_reset_form.html"
    email_template_name = "core/emails/password_reset_email.txt"
    subject_template_name = "core/emails/password_reset_subject.txt"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not allow_auth_action(client_ip(request), "password_reset"):
            return render(
                request,
                self.template_name,
                {
                    "form": self.get_form(),
                    "rate_limited": True,
                    "rate_limit_message": _AUTH_RATE_LIMIT_MESSAGE,
                },
                status=429,
            )
        return super().post(request, *args, **kwargs)
