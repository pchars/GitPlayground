# GitPlayground

Web training platform for practicing Git with theory modules and interactive tasks.

## Requirements

- Python 3.12+
- Git (for sandbox tasks)
- Optional: Docker and Docker Compose for the full dev stack (web + Celery + Redis)

## Quick start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python manage.py migrate
python manage.py seed_initial_data
python manage.py seed_quiz_questions
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

To refresh theory text in the database without reseeding all tasks:

```bash
python manage.py sync_theory_content
```

## Quick start (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_initial_data
.\.venv\Scripts\python.exe manage.py seed_quiz_questions
.\.venv\Scripts\python.exe manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

To refresh theory text in the database without reseeding all tasks:

```powershell
.\.venv\Scripts\python.exe manage.py sync_theory_content
```

## Quiz and theory content

Квиз по Git (`/quiz/`): один вопрос и четыре варианта, большой банк вопросов загружается командой `seed_quiz_questions` (повторный запуск без `--force` не дублирует записи).

**Теория в UI** берётся из базы (`TheoryBlock` и связанные сущности). Исходный текст при первичном наполнении задаётся в коде команды [`seed_initial_data`](apps/tasks/management/commands/seed_initial_data.py) (в т.ч. константа `THEORY_CONTENT`).

`sync_theory_content` обновляет записи теории в БД из того же источника, что и сид, без полного пересоздания всех задач. Полный `seed_initial_data` перезаписывает теорию и заново прогоняет задачи и ассеты.

Подробности продакшен-окружения: [docs/DEPLOY.md](docs/DEPLOY.md). Эксплуатация: [docs/OPERATIONS.md](docs/OPERATIONS.md). Описание JSON API плейграунда: [docs/openapi/playground.yaml](docs/openapi/playground.yaml). Дизайн-система и фронтенд: [DESIGN.md](DESIGN.md), [docs/FRONTEND.md](docs/FRONTEND.md). Инструкции для AI-агентов: [AGENTS.md](AGENTS.md) (ролевые playbooks — [.cursor/agents/](.cursor/agents/)). Полный индекс документации: [docs/README.md](docs/README.md).

## Docker dev stack

```bash
docker compose up --build
```

This starts:
- `web` Django app
- `worker` Celery worker
- `redis` broker/backend

Useful commands inside Docker:

```bash
docker compose exec web python manage.py sync_theory_content
docker compose exec web python manage.py seed_quiz_questions
```

## Tests

Перед коммитом:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m coverage run manage.py test
.\.venv\Scripts\python.exe -m coverage report
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Порог покрытия — не ниже 52% (`pyproject.toml`).

macOS / Linux:

```bash
source .venv/bin/activate
python manage.py test
```

Windows:

```powershell
.\.venv\Scripts\python.exe manage.py test
```
