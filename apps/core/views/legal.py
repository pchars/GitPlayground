"""Legal documentation and support pages."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.users.legal import MARKETING_CONSENT_VERSION, PRIVACY_POLICY_VERSION


def privacy_policy(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/legal/privacy_policy.html",
        {"policy_version": PRIVACY_POLICY_VERSION},
    )


def marketing_consent_info(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/legal/marketing_consent.html",
        {"consent_version": MARKETING_CONSENT_VERSION},
    )


def support_donate(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/support_donate.html",
        {
            "wallet_address": settings.DONATION_CRYPTO_WALLET,
            "wallet_label": settings.DONATION_CRYPTO_WALLET_LABEL,
        },
    )