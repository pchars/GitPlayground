# Документация GitPlayground

Навигация по технической документации репозитория.

| Документ | Описание |
| --- | --- |
| [../DESIGN.md](../DESIGN.md) | Дизайн-система: токены, типографика, компоненты, адаптив |
| [FRONTEND.md](FRONTEND.md) | CSS/HTML-архитектура, статика, шаблоны |
| [DEPLOY.md](DEPLOY.md) | Чеклист деплоя и переменные окружения |
| [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) | Контракт `validator.py` для задач |
| [API.md](API.md) | Зачем OpenAPI, кому полезен, что не светить в проде |
| [openapi/playground.yaml](openapi/playground.yaml) | OpenAPI 3.0: JSON API плейграунда (run, files, validate, reset, hint) |
| [../AGENTS.md](../AGENTS.md) | Правила для агентов и контрибьюторов |
| [../README.md](../README.md) | Быстрый старт и обзор проекта |

## Структура приложения

Django-проект с приложениями в `apps/`:

- `core` — страницы, плейграунд, сервисный слой
- `tasks` — уровни, задачи, теория, сиды
- `sandbox` — сессии песочницы
- `progress` — попытки, прогресс, лидерборд
- `achievements` — достижения
- `quiz` — квиз
- `users` — профиль и баллы

Шаблоны — `templates/`, статика — `static/`, настройки — `gitplayground/settings.py`.

## Типовой цикл разработки

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

После изменений в плейграунде — полный clean cycle из `AGENTS.md` (очистка `.sandboxes/`, остановка сессий, перезапуск `runserver`).
