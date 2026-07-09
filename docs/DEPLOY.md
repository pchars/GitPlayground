# Чеклист деплоя GitPlayground

## Обязательные переменные окружения

| Переменная | Назначение |
| --- | --- |
| `DJANGO_DEBUG` | `false` в продакшене |
| `DJANGO_SECRET_KEY` | Уникальный длинный ключ (не значение по умолчанию из репозитория) |
| `DJANGO_ALLOWED_HOSTS` | Список доменов через запятую |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://ваш-домен` для HTTPS-форм и AJAX |

## Песочница

| Переменная | Рекомендация |
| --- | --- |
| `SANDBOX_ENGINE` | В продакшене — `docker` |
| `SANDBOX_ALLOW_LOCAL_FALLBACK` | `false`, чтобы не выполнять команды на хосте при недоступности Docker |
| `SANDBOX_DOCKER_IMAGE` | Образ с Git; пересобирайте при обновлении зависимостей |

Подробности политики команд — в `AGENTS.md` (раздел Sandbox command policy).

## Celery / Redis

- Настройте `CELERY_BROKER_URL` и `CELERY_RESULT_BACKEND` на рабочий Redis.
- Запустите worker и beat: в `CELERY_BEAT_SCHEDULE` уже есть `cleanup_expired_sandboxes` (каждые 5 минут).

## Статика

После выкладки кода:

```bash
python manage.py collectstatic --noinput
```

Статические файлы лежат в `static/`; после collect — в `staticfiles/`. CSS организован по страницам (см. [FRONTEND.md](FRONTEND.md)).

**Не** публикуйте каталог `docs/` как веб-статику в продакшене (OpenAPI и внутренняя документация — только в репозитории). Подробнее: [API.md](API.md).

## База данных и сиды

На чистой БД:

```bash
python manage.py migrate
python manage.py seed_initial_data
python manage.py seed_quiz_questions
```

Только обновление теории без пересоздания задач:

```bash
python manage.py sync_theory_content
```

## Проверка перед выкладкой

```bash
python manage.py check --deploy
python manage.py test
python manage.py makemigrations --check --dry-run
```

При `DJANGO_DEPLOY_CHECK=1` и `DEBUG=false` приложение дополнительно проверит: `SECRET_KEY`, `ALLOWED_HOSTS`, `SANDBOX_ENGINE=docker`, отсутствие явного `SANDBOX_ALLOW_LOCAL_FALLBACK`.

## Docker Compose (dev / staging)

```bash
docker compose up --build
```

Сервисы: `web`, `worker`, `redis`. В контейнере:

```bash
docker compose exec web python manage.py seed_initial_data
docker compose exec web python manage.py seed_quiz_questions
```

## См. также

- [README.md](README.md) — оглавление документации
- [OPERATIONS.md](OPERATIONS.md) — эксплуатация и мониторинг
- [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) — выполнение `validator.py`
- [openapi/playground.yaml](openapi/playground.yaml) — JSON API плейграунда
- [../AGENTS.md](../AGENTS.md) — политики разработки
