# Контракт валидатора задачи

Валидатор — **один файл** `validator.py` в корне рабочей копии репозитория песочницы (тот же каталог, что и для команд Git).

## Поведение

1. Платформа записывает в `validator.py` содержимое ассета типа `VALIDATOR` из БД (если ассет задан и не пустой).
2. **Локальная песочница**: `sys.executable validator.py` с `cwd` = корень репозитория.
3. **Docker-песочница**: `docker exec <container> python3|python validator.py` без оболочки; рабочий каталог — `/workspace`. Контейнер с `--network none`, лимиты CPU/RAM/pids — см. `SANDBOX_DOCKER_*` в `apps/core/services/sandbox_ops.py`.
4. Таймаут — `session.timeout_seconds` (модель `SandboxSession`).
5. Код возврата `0` → вердикт `PASSED`; иной код → `FAILED`; таймаут или исключение → `ERROR`.

## Ограничения для авторов

- Без сети (в Docker она отключена).
- Только файлы внутри корня репозитория; не полагайтесь на пути вне workspace.
- Ветка по умолчанию — **`main`** (см. `git_env()` в `sandbox_ops.py`).

## Добавление задачи

1. Описание и баллы — `TASK_BLUEPRINTS` в `seed_initial_data.py`.
2. Текст валидатора — `TASK_VALIDATORS` или `_validator_by_slug`.
3. Золотое решение — `SOLUTIONS` в `apps/core/tests/test_task_solvability.py` (обязательно для каждой задачи).

Подробнее об авторинге — раздел «Authoring a task» в `AGENTS.md`.

## См. также

- [README.md](README.md)
- [FRONTEND.md](FRONTEND.md) — UI плейграунда
- [openapi/playground.yaml](openapi/playground.yaml) — endpoint `validate`
