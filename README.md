# GitPlayground

Платформа для практики Git: теория по уровням, квиз и интерактивные задачи в изолированной песочнице с автоматической проверкой.

## Требования

- Python 3.12+
- Git (команды в задачах)
- БД: **SQLite** (`db.sqlite3` в корне проекта, путь — `SQLITE_DB_PATH`)
- Опционально: Docker и Docker Compose (песочница + Celery + Redis)

## Быстрый старт (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env   # DJANGO_DEBUG=true — нужен для локальной песочницы без Docker
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_initial_data
.\.venv\Scripts\python.exe manage.py seed_quiz_questions
.\.venv\Scripts\python.exe manage.py runserver
```

В `.env` для локалки оставьте `DJANGO_DEBUG=true`. Статику (CSS/JS) отдаёт WhiteNoise — при `DEBUG=false` перезапустите сервер после `pip install -e .`.

Откройте [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

### Перезапуск после обновления кода

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
if (Test-Path ".\.sandboxes") { Get-ChildItem ".\.sandboxes" -Force | Remove-Item -Recurse -Force }
.\.venv\Scripts\python.exe manage.py shell -c "from apps.sandbox.models import SandboxSession; SandboxSession.objects.exclude(status=SandboxSession.Status.STOPPED).update(status=SandboxSession.Status.STOPPED)"
.\.venv\Scripts\python.exe manage.py runserver
```

Перед первым деплоем с `DJANGO_DEBUG=false`: `manage.py collectstatic --noinput` (см. [docs/DEPLOY.md](docs/DEPLOY.md)).

## Быстрый старт (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
cp .env.example .env
python manage.py migrate
python manage.py seed_initial_data
python manage.py seed_quiz_questions
python manage.py runserver
```

В `.env` для локалки: `DJANGO_DEBUG=true`. После обновления зависимостей: `pip install -e .`, очистка `.sandboxes/`, перезапуск `runserver` (см. блок выше в Windows-разделе).

## Контент: теория и квиз

- **Квиз** (`/quiz/`) — банк вопросов загружается `seed_quiz_questions` (без `--force` не дублирует записи).
- **Теория в UI** — из БД (`TheoryBlock`). Исходник при сиде: `apps/tasks/management/commands/seed_initial_data.py`.
- **Только обновить теорию** без пересоздания задач: `sync_theory_content`.

## Docker (dev)

```bash
docker compose up --build
```

Сервисы: `web`, `worker`, `redis`. В контейнере: `docker compose exec web python manage.py sync_theory_content`.

## Тесты

Порядок как в CI — см. [AGENTS.md](AGENTS.md):

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m coverage run manage.py test --exclude-tag=slow
.\.venv\Scripts\python.exe -m coverage run -a manage.py test --tag=slow
.\.venv\Scripts\python.exe -m coverage report
```

Порог покрытия — ≥ 52% (`pyproject.toml`). Быстрый прогон без golden-solution harness: `manage.py test --exclude-tag=slow`.

## Документация

| Документ | Назначение |
| --- | --- |
| [docs/README.md](docs/README.md) | Индекс документации |
| [docs/PRODUCT.md](docs/PRODUCT.md) | Путь ученика и механики |
| [docs/DESIGN.md](docs/DESIGN.md) | Дизайн-система |
| [docs/FRONTEND.md](docs/FRONTEND.md) | CSS, шаблоны, JSON API плейграунда |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Деплой |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Эксплуатация и CI |
| [docs/VALIDATOR_CONTRACT.md](docs/VALIDATOR_CONTRACT.md) | Контракт `validator.py` |
| [AGENTS.md](AGENTS.md) | Правила для разработчиков и AI-агентов |
