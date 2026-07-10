# Документация GitPlayground

Краткий индекс для разработчиков и контрибьюторов. Пользовательский интерфейс — на русском; код и имена файлов — на английском.

## Для кого что читать

| Роль | Документ |
| --- | --- |
| Новый разработчик | [../README.md](../README.md) → [../AGENTS.md](../AGENTS.md) |
| Автор задач / валидаторов | [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) + раздел Authoring в AGENTS |
| Фронтенд / UI | [DESIGN.md](DESIGN.md), [FRONTEND.md](FRONTEND.md) |
| Деплой / on-call | [DEPLOY.md](DEPLOY.md), [OPERATIONS.md](OPERATIONS.md) |
| Продукт / контент | [PRODUCT.md](PRODUCT.md) |

## Содержание

| Документ | Описание |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | Ценность, путь ученика, прогресс и баллы |
| [FRONTEND.md](FRONTEND.md) | CSS/HTML, JS, JSON API плейграунда |
| [VALIDATOR_CONTRACT.md](VALIDATOR_CONTRACT.md) | Как работает `validator.py` |
| [DEPLOY.md](DEPLOY.md) | Переменные окружения и чеклист выкладки |
| [OPERATIONS.md](OPERATIONS.md) | Песочница, логи, CI, security-сканы |
| [DESIGN.md](DESIGN.md) | Токены, типографика, компоненты |
| [../AGENTS.md](../AGENTS.md) | Архитектура, тесты, политика песочницы |
| [../README.md](../README.md) | Быстрый старт |

## Структура кода

Приложения в `apps/`: `core`, `tasks`, `sandbox`, `progress`, `achievements`, `quiz`, `users`.

Шаблоны — `templates/`, статика — `static/`, настройки — `gitplayground/settings.py`.

## Типовой цикл

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe manage.py test --exclude-tag=slow
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

После изменений плейграунда — clean cycle из `AGENTS.md` (очистка `.sandboxes/`, остановка сессий, перезапуск `runserver`).
