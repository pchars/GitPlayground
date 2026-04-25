# Чеклист деплоя GitPlayground

## Обязательные переменные окружения

- **`DJANGO_DEBUG`**: `false` в продакшене.
- **`DJANGO_SECRET_KEY`**: уникальный длинный ключ (не значение по умолчанию из репозитория).
- **`DJANGO_ALLOWED_HOSTS`**: список доменов через запятую.
- **`DJANGO_CSRF_TRUSTED_ORIGINS`**: `https://ваш-домен` для HTTPS-форм и AJAX.

## Песочница

- **`SANDBOX_ENGINE`**: в продакшене рекомендуется `docker`.
- **`SANDBOX_ALLOW_LOCAL_FALLBACK`**: в продакшене установите `false`, чтобы не выполнять команды на хосте при недоступности Docker.
- **`SANDBOX_DOCKER_IMAGE`**: образ с Git и ограниченным окружением; пересобирайте при обновлении зависимостей.

## Celery / Redis

- Настройте **`CELERY_BROKER_URL`** и **`CELERY_RESULT_BACKEND`** на рабочий Redis.
- Запустите worker и beat: в `CELERY_BEAT_SCHEDULE` уже есть периодическая задача `cleanup_expired_sandboxes` (каждые 5 минут).

## Проверка перед выкладкой

```bash
python manage.py check --deploy
```

При установке **`DJANGO_DEPLOY_CHECK=1`** приложение при старте дополнительно проверит (только если `DEBUG=false`): `SECRET_KEY`, `ALLOWED_HOSTS`, **`SANDBOX_ENGINE=docker`**, и что **`SANDBOX_ALLOW_LOCAL_FALLBACK`** не включён явно через env.

## См. также

- [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) — как выполняется `validator.py` в локальной и Docker-песочнице.
- [openapi/playground.yaml](openapi/playground.yaml) — черновое описание JSON API плейграунда.
