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

### Management-команды (ops)

| Команда | Назначение |
| --- | --- |
| `snapshot_leaderboard` | Зафиксировать снимок таблицы лидеров (`LeaderboardSnapshot`) |
| `reconcile_points` | Сверить `UserProfile.total_points` с суммой `PointLedgerEntry` |
| `sync_theory_content` | Обновить теорию из `theory_content.py` без пересида задач |

Импорт задачи из ZIP — в Django Admin: `/admin/tasks/task/upload/` (preview + import).

## Статика и кэш

- `collectstatic` перед выкладкой.
- Версионирование URL: тег `{% static_v 'path' %}` (хэш содержимого). После деплоя CSS/JS обновляются без ручного `?v=`.

## Мониторинг (рекомендации)

- Диск: размер `.sandboxes/`, рост при сбое Celery cleanup.
- HTTP 503 на `/playground/.../run/` — недоступность Docker или исчерпание ресурсов.
- HTTP 429 — rate limit плейграунда (`apps/core/playground_limits.py`).
- Покрытие тестов ≥ 52% (`pyproject.toml`); CI: `manage.py test`, `makemigrations --check`.

## CI: тесты, линт и безопасность

| Workflow | Job | Что проверяет |
| --- | --- | --- |
| `ci.yml` | `test` | ruff, миграции, fast-тесты + slow harness, coverage ≥ 52% |
| `ci.yml` | `e2e-smoke` | Playwright: лендинг, навигация, вход |
| `security.yml` | `semgrep` | SAST: Python, Django, JS/TS, HTML, CSS, secrets, OWASP |
| `security.yml` | `trivy-fs` / `trivy-image` | Уязвимости зависимостей, секреты, misconfig, Docker-образ |

**Semgrep** сканирует все файлы, отслеживаемые git (шаблоны `.html`, `static/js`, `static/css`, Python).
Исключения — `.semgrepignore` и `--exclude` в workflow (`.sandboxes`, `.venv`, `node_modules`, `.cursor`).

**Trivy FS** требует lockfile-манифесты: голый `pyproject.toml` не даёт vuln-скану целей. Job
`trivy-fs` перед сканом:

1. `pip install -e .` → `requirements.trivy.txt` (`pip freeze`, в `.gitignore`);
2. проверяет наличие `e2e/package-lock.json` (или генерирует `npm install --package-lock-only`).

Общие настройки сканеров — `trivy.yaml` (severity CRITICAL/HIGH/MEDIUM, scanners vuln/secret/misconfig).
Версия Trivy в CI: `TRIVY_VERSION` в `security.yml` (сейчас v0.72.0, `skip-version-check` в конфиге).

Локально (нужен Docker):

```bash
# Semgrep
docker run --rm -v "$PWD:/src" -w /src returntocorp/semgrep:1.168.0 semgrep scan \
  --config p/python --config p/django --config p/javascript --config p/typescript \
  --config p/secrets --config p/owasp-top-ten \
  --exclude-rule python.django.security.django-no-csrf-token.django-no-csrf-token \
  --metrics=off

# Trivy FS — сначала materialize lockfile
pip install -e .
pip freeze | grep -viE '^(-e |gitplayground==)' > requirements.trivy.txt
docker run --rm -v "$PWD:/src" -w /src aquasec/trivy:0.72.0 fs -c trivy.yaml .
```

Отдельный ESLint/Stylelint в CI **не обязателен**: ruff закрывает Python, Semgrep — security-паттерны
во frontend; стилевой JS/CSS объём мал и покрыт code review + ponytail-правилами.

Для правок security CI: [security-engineer](../.cursor/agents/security-engineer.md) (workflow, Trivy, sandbox);
для аудита логов и рисков: [security-auditor](../.cursor/agents/security-auditor.md).

## См. также

- [DEPLOY.md](DEPLOY.md) — переменные окружения и pre-flight
- [FRONTEND.md](FRONTEND.md) — JSON API плейграунда
- [PRODUCT.md](PRODUCT.md) — путь ученика
