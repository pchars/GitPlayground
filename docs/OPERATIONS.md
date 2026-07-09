# Эксплуатация GitPlayground

Руководство для администраторов и on-call. Чеклист первичного деплоя — в [DEPLOY.md](DEPLOY.md).

## Процессы

| Процесс | Назначение |
| --- | --- |
| `web` (gunicorn / `runserver`) | HTTP, плейграунд, теория, квиз |
| `worker` (Celery) | Фоновые задачи |
| `beat` (Celery Beat) | Периодическая очистка песочниц (`cleanup_expired_sandboxes`, каждые 5 мин) |
| `redis` | Брокер и backend Celery |

Без worker/beat истёкшие сессии песочницы не удаляются автоматически; диск `.sandboxes/` будет расти.

## Песочница

- Рабочие каталоги: `.sandboxes/` (gitignored, вне `collectstatic`).
- В продакшене: `SANDBOX_ENGINE=docker`, `SANDBOX_ALLOW_LOCAL_FALLBACK=false`.
- Политика команд — [AGENTS.md](../AGENTS.md) (раздел Sandbox command policy); блоклист в `apps/core/services/command_policy.py`.
- Ручная очистка dev-окружения (см. AGENTS.md):

```powershell
if (Test-Path ".\.sandboxes") { Get-ChildItem ".\.sandboxes" -Force | Remove-Item -Recurse -Force }
.\.venv\Scripts\python.exe manage.py shell -c "from apps.sandbox.models import SandboxSession; SandboxSession.objects.exclude(status=SandboxSession.Status.STOPPED).update(status=SandboxSession.Status.STOPPED)"
```

## Логи и аудит

| Logger | События |
| --- | --- |
| `apps.core.playground` | JSON: `playground_api` (run, validate, hint, reset) |
| `apps.core.sandbox.audit` | JSON: `sandbox_command_policy`, операции с файлами |

Поля: `user_id`, `task_external_id`, `session_id`, `latency_ms`, `verdict`, `allowed`/`reason` для отклонённых команд.

## База данных

- SQLite по умолчанию; Postgres через `DB_*` (см. `settings.py`).
- После миграций на чистой БД: `seed_initial_data`, `seed_quiz_questions`.
- Только теория: `sync_theory_content`.

## Статика и кэш

- `collectstatic` перед выкладкой.
- Версионирование URL: тег `{% static_v 'path' %}` (хэш содержимого). После деплоя CSS/JS обновляются без ручного `?v=`.

## Мониторинг (рекомендации)

- Диск: размер `.sandboxes/`, рост при сбое Celery cleanup.
- HTTP 503 на `/playground/.../run/` — недоступность Docker или исчерпание ресурсов.
- HTTP 429 — rate limit плейграунда (`apps/core/playground_limits.py`).
- Покрытие тестов ≥ 52% (`pyproject.toml`); CI: `manage.py test`, `makemigrations --check`.

## См. также

- [DEPLOY.md](DEPLOY.md) — переменные окружения и pre-flight
- [API.md](API.md) — OpenAPI плейграунда
- [PRODUCT.md](PRODUCT.md) — путь ученика
