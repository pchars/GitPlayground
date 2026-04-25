"""Публичные страницы и служебные HTTP-эндпоинты."""

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
import redis

from apps.progress.models import TaskCompletion
from apps.tasks.models import Level, Task


def landing(request):
    students_total = User.objects.count()
    students_solved = TaskCompletion.objects.values("user_id").distinct().count()
    tasks_total = Task.objects.count()
    completions_total = TaskCompletion.objects.count()
    levels_total = Level.objects.count()
    return render(
        request,
        "core/landing.html",
        {
            "students_total": students_total,
            "students_solved": students_solved,
            "tasks_total": tasks_total,
            "completions_total": completions_total,
            "levels_total": levels_total,
        },
    )


def healthcheck(request: HttpRequest) -> JsonResponse:
    checks = {"database": False, "redis": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = True
    except Exception:  # noqa: BLE001
        checks["database"] = False

    try:
        parsed = urlparse(settings.CELERY_BROKER_URL)
        if parsed.scheme.startswith("redis"):
            client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            checks["redis"] = bool(client.ping())
        else:
            checks["redis"] = True
    except Exception:  # noqa: BLE001
        checks["redis"] = False
    status = "ok" if all(checks.values()) else "degraded"
    return JsonResponse({"status": status, "service": "gitplayground", "checks": checks})
