"""User-facing HTTP error pages (production-safe, no debug details)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(
        request,
        "core/errors/404.html",
        {"path": request.path},
        status=404,
    )


def server_error(request: HttpRequest) -> HttpResponse:
    return render(request, "core/errors/500.html", status=500)


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "core/errors/403.html", status=403)


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "core/errors/400.html", status=400)
