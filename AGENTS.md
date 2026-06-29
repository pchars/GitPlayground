# AGENTS.md

Guidance for AI agents and contributors working in this repository. Keep changes
small, run the test suite, and respect the security posture of the sandbox.

## What this project is

GitPlayground is a Django web app for learning Git: theory modules, an interactive
quiz, and hands-on tasks solved in a **sandboxed terminal** that runs real `git`
commands and grades the result with a per-task `validator.py`.

- **Stack:** Django 6, Python 3.12+, SQLite by default (Postgres via `DB_*` env vars),
  Celery + Redis for background work, `markdown` + Mermaid for theory rendering.
- **Entry point:** `manage.py`; project settings in `gitplayground/settings.py`;
  root URLConf in `gitplayground/urls.py`.

## Architecture & app boundaries

Apps live under `apps/`:

| App | Responsibility |
| --- | --- |
| `core` | Views, the playground UI/JSON API, and the service layer (`apps/core/services/`). Has **no models**. |
| `tasks` | Content models (`Level`, `Task`, `TaskAsset`, `TaskRevision`, `TheoryBlock`), the `seed_initial_data` source of truth, and `theory_content.py`. |
| `sandbox` | `SandboxSession` model (one sandbox per user+task). |
| `progress` | Attempts, completions, hint usage, revision progress, leaderboard snapshots. |
| `achievements` | Achievement definitions + awarding (`services.py`). |
| `quiz` | Quiz questions, progress, and stats. |
| `users` | `UserProfile` and the points ledger. |

Key service modules (import these via the `apps.core.services` facade):

- `apps/core/services/sandbox_ops.py` — session lifecycle, the **command policy/allowlist**,
  file read/write, and the deterministic `git_env()`.
- `apps/core/services/learn_ops.py` — `validate_task`, hint unlocking, and the linear
  unlock logic (`get_next_unlockable_task_for_user`, `can_open_task`). Views must reuse
  these helpers rather than re-implementing unlock rules.

## Common commands

Use the project virtualenv (`.venv`). On Windows PowerShell, `&&` is not supported —
chain with `;` or run commands separately.

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_initial_data      # levels, tasks, theory, validators, achievements
.\.venv\Scripts\python.exe manage.py seed_quiz_questions
.\.venv\Scripts\python.exe manage.py runserver
```

Tests, coverage gate, and migration check (run before every commit):

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m coverage run manage.py test
.\.venv\Scripts\python.exe -m coverage report          # must stay >= 52% (pyproject fail_under)
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run   # must report "No changes detected"
```

`sync_theory_content` updates only the theory blocks in the DB from
`apps/tasks/theory_content.py` without rebuilding tasks.

## Clean dev cycle after every code change (required)

After **any** code change, before telling the user something is ready to check, run the
full clean cycle so the user always lands on a fresh, junk-free state. Sandbox state is
persisted on disk and survives a server restart, so a plain `runserver` restart is **not**
enough on its own.

1. **Clear ephemeral sandbox state.** Workspaces, terminal logs, and the managed git
   config live under `.sandboxes/` (gitignored) and accumulate across runs. Wipe them:

```powershell
if (Test-Path ".\.sandboxes") { Get-ChildItem ".\.sandboxes" -Force | Remove-Item -Recurse -Force }
```

2. **Stop stale sessions** so the DB no longer points at deleted workspaces (the next page
   load reseeds a fresh workspace with an empty terminal log):

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apps.sandbox.models import SandboxSession; SandboxSession.objects.exclude(status=SandboxSession.Status.STOPPED).update(status=SandboxSession.Status.STOPPED)"
```

3. **Restart the server** (stop the running `runserver`, then start it again):

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Only after this full cycle should the user be asked to reload the page / verify behavior.
`.sandboxes/_logs/session_<id>.terminal.log` is the per-session terminal history shown on
page load; clearing it (step 1) is what removes leftover "junk" output.

## Sandbox command policy (security-critical)

User input is **not** run through a shell. `_parse_user_command` in
`sandbox_ops.py` enforces a strict allowlist; anything else returns exit code `126`
(`command_not_allowed`) and is audit-logged (`sandbox_command_policy`). Allowed forms:

- `git ...` (any git subcommand)
- `ls` / `ls <path>` (read-only listing, implemented in Python; flags accepted but ignored)
- `pwd`
- `mkdir <dir>` / `mkdir -p <dir>`
- `touch <file>`
- `cat <file>`
- `type nul > <file>`
- `echo <text> > <file>` and `echo <text> >> <file>`

Non-`git` verbs are executed in pure Python (no subprocess, no shell) and guarded by
`_resolve_repo_relative_path` + the `..` check, so they cannot escape the workspace.

Multi-line file content uses the file-editor API (`read_text_file_from_repo` /
`write_text_file_to_repo`), not shell redirection. When a task needs a capability
that isn't allowed, prefer rewriting the task to use `git` / the editor over widening
the allowlist; only extend `_parse_user_command` when genuinely required, and keep the
"no arbitrary shell" guarantee.

Git runs with a deterministic environment from `git_env()`: a managed global config
that pins `init.defaultBranch=main`, a fixed identity, `safe.directory=*`, and disables
system config. **Tasks and validators must assume the default branch is `main`.**

## Validator contract

See `docs/VALIDATOR_CONTRACT.md`. In short: a task's `VALIDATOR` asset is written to
`validator.py` at the repo root and executed (`python validator.py`); exit `0` = pass,
non-zero = fail, timeout/exception = error. Validators must not use the network and may
only inspect files within the repo working directory.

## Migration policy

Each app keeps a **single `0001_initial`** migration. Do not add incremental migrations
for routine model changes during development — instead delete the app's numbered
migration(s) (keep `__init__.py`), run `makemigrations`, recreate the dev DB
(`db.sqlite3` is gitignored), and reseed. `makemigrations --check` must stay clean in CI.
On a fresh DB, achievement criterion fields are written by `bootstrap_default_achievements`
(invoked by `seed_initial_data`), so no data migration is needed.

## Authoring a task

Tasks are defined in `apps/tasks/management/commands/seed_initial_data.py`:

1. Add a `(slug, description, points)` entry to `TASK_BLUEPRINTS[level]`.
2. Provide a validator: add a `TASK_VALIDATORS["<level>.<n>"]` entry or a branch in
   `_validator_by_slug`. Keep validators **honest** — only check what the learner can
   actually achieve in the no-network sandbox; align the `description` with the check.
3. If the task needs a starting state, extend `build_start_repo_asset` (zip-based) or the
   `metadata["start"]["requires"]` handling in `_seed_workspace_from_assets`
   (`repo_initialized`, `hello_committed`, `feature_branch_exists`).
4. **Add an intended solution** to `SOLUTIONS` in
   `apps/core/tests/test_task_solvability.py`. This golden-solution harness runs your
   solution through the real sandbox + validator and asserts `PASSED`, and it fails if a
   seeded task has no registered solution. Every task must be provably solvable.

## Conventions

- Lint/format with **ruff** (config in `pyproject.toml`).
- Keep the **coverage gate at >= 52%**.
- Business logic belongs in `apps/core/services/`; keep views thin (use the
  `_acquire_session` guard in `playground.py` rather than re-adding lock/rate/session
  boilerplate).
- Only the GitHub track is seeded; there is no GitLab content.
- Comments and user-facing strings are in Russian to match the existing codebase; code
  identifiers are in English.
- Commit messages: imperative summary line; follow the repo rule of committing and
  pushing each completed unit of work.
