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

Статику отдаёт **WhiteNoise** (работает и при `DJANGO_DEBUG=false`). Исходники — каталог `static/`.

Рекомендуется перед выкладкой:

```bash
python manage.py collectstatic --noinput
```

После collect можно выставить `WHITENOISE_USE_FINDERS=false` (файлы берутся только из `staticfiles/`).

Каталог `docs/` **не** публикуйте как веб-статику — это документация репозитория, не часть продукта.

## База данных и сиды

БД — **SQLite** (`db.sqlite3` или `SQLITE_DB_PATH`). Других движков не предусмотрено.

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
python manage.py test --exclude-tag=slow
python manage.py test --tag=slow
python manage.py makemigrations --check --dry-run
```

При `DJANGO_DEPLOY_CHECK=1` и `DEBUG=false` приложение дополнительно проверит: `SECRET_KEY`, `ALLOWED_HOSTS`, `SANDBOX_ENGINE=docker`, отсутствие явного `SANDBOX_ALLOW_LOCAL_FALLBACK`.

## Страницы ошибок

При `DJANGO_DEBUG=false` Django отдаёт пользовательские шаблоны (без технических деталей):

| Код | Шаблон |
| --- | --- |
| 400 | `templates/core/errors/400.html` |
| 403 | `templates/core/errors/403.html` |
| 404 | `templates/core/errors/404.html` |
| 500 | `templates/core/errors/500.html` |

Обработчики: `gitplayground/urls.py` (`handler400` … `handler500`). При `DEBUG=true` для 404 Django показывает отладочную страницу — это нормально для локальной разработки.

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

- [README.md](../README.md) — быстрый старт
- [OPERATIONS.md](OPERATIONS.md) — эксплуатация и мониторинг
- [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) — выполнение `validator.py`
- [FRONTEND.md](FRONTEND.md) — JSON API плейграунда
- [../AGENTS.md](../AGENTS.md) — политики разработки
