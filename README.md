# GitPlayground

Web training platform for practicing Git with theory modules and interactive tasks.

## Quick start

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_initial_data
.\.venv\Scripts\python.exe manage.py seed_quiz_questions
.\.venv\Scripts\python.exe manage.py runserver
```

Квиз по Git (`/quiz/`): один вопрос и четыре варианта, большой банк вопросов загружается командой `seed_quiz_questions` (повторный запуск без `--force` не дублирует записи).

**Теория в UI** берётся из базы (`TheoryBlock` и связанные сущности). Исходный текст при первичном наполнении задаётся в коде команды [`seed_initial_data`](apps/tasks/management/commands/seed_initial_data.py) (в т.ч. константа `THEORY_CONTENT`); чтобы изменения из кода попали в БД, выполните `seed_initial_data` или точечно:

```powershell
.\.venv\Scripts\python.exe manage.py sync_theory_content
```

`sync_theory_content` обновляет записи теории в БД из того же источника, что и сид, без полного пересоздания всех задач. Полный `seed_initial_data` перезаписывает теорию и заново прогоняет задачи и ассеты.

Подробности продакшен-окружения: [docs/DEPLOY.md](docs/DEPLOY.md). Описание JSON API плейграунда: [docs/openapi/playground.yaml](docs/openapi/playground.yaml).

В Docker:

```bash
docker compose exec web python manage.py sync_theory_content
docker compose exec web python manage.py seed_quiz_questions
```

## Docker dev stack

```bash
docker compose up --build
```

This starts:
- `web` Django app
- `worker` Celery worker
- `redis` broker/backend
