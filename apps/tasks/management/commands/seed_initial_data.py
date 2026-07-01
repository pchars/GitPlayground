import base64
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
import zipfile

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.tasks.models import Level, Task, TaskAsset, TheoryBlock, TaskRevision
from apps.tasks.theory_content import LEVEL_DIAGRAMS, LEVEL_SECTION_HINTS, THEORY_CONTENT


LEVELS = [
    (1, "Основы Git", 8),
    (2, "Ветвление", 7),
    (3, "Слияния и интеграция", 7),
    (4, "История и переписывание", 6),
    (5, "Удаленные репозитории и командная работа", 6),
    (6, "Диагностика, внутренности и автоматизация", 6),
    (7, "Гигиена репозитория: .gitignore и .gitkeep", 5),
    (8, "Тегирование и фиксация версий", 5),
]

TASK_BLUEPRINTS = {
    1: [
        ("init_repo", "Инициализируй репозиторий в текущей папке (`git init`).", 6),
        ("first_commit", "Создай `hello.txt` с текстом `Hello, Git!`, добавь в индекс и сделай коммит `Add hello`.", 10),
        ("check_status", "Измени `hello.txt` и проверь, что изменение не в staging (`git status --short`).", 6),
        ("stage_unstage", "Цель — снять файл со staging, не теряя правку. Измени `hello.txt`, добавь его в индекс (`git add hello.txt`), затем убери из индекса командой `git restore --staged hello.txt`. Важно различать: `git restore --staged <файл>` снимает файл со staging (это и нужно), а `git restore <файл>` без `--staged` откатывает саму правку в рабочей копии. Итог: в `git status --short` файл показан как ` M` — изменён, но не застейджен.", 8),
        ("view_diff", "Добавь строку `Another line` в `hello.txt` и выполни `git diff`, чтобы увидеть это изменение до коммита.", 6),
        ("commit_second", "Сделай второй коммит с сообщением `Update hello`.", 10),
        ("amend_commit", "Добавь `config.txt` в последний коммит через `--amend`.", 12),
        ("view_history", "Покажи историю в компактном виде (`git log --oneline`).", 6),
    ],
    2: [
        ("create_branch", "Создай и открой ветку `feature-x`.", 8),
        ("commit_on_branch", "На `feature-x` добавь `feature.txt` и закоммить.", 10),
        ("switch_branch", "Вернись в `main` и убедись, что `feature.txt` исчез из рабочей копии.", 6),
        ("list_branches", "Покажи список веток и текущую ветку (`git branch`).", 5),
        ("rename_branch", "Переименуй рабочую ветку в более понятное имя.", 8),
        ("branch_from_commit", "Создай ветку от выбранного SHA из истории.", 12),
        ("delete_branch", "Удаляй ненужную ветку безопасной командой (не активную).", 7),
    ],
    3: [
        ("fast_forward_merge", "Слей ветку в fast-forward без merge-коммита.", 8),
        ("no_ff_merge", "Сделай merge с `--no-ff`, чтобы получить явный merge-коммит.", 12),
        ("resolve_conflict", "Разреши конфликт вручную и корректно заверши merge.", 18),
        ("abort_merge", "Запусти конфликт и откати его через `git merge --abort`.", 10),
        ("squash_merge", "Слей ветку в один squashed commit.", 14),
        ("cherry_pick_hotfix", "Перенеси один нужный коммит через `git cherry-pick`.", 12),
        ("revert_merge", "Откати merge-коммит через `git revert -m`.", 14),
    ],
    4: [
        ("amend_message", "Исправь сообщение последнего коммита через `--amend`.", 8),
        ("reorder_commits", "Через `rebase -i` поменяй порядок последних коммитов.", 14),
        ("squash_commits", "Объедини несколько соседних коммитов в один.", 14),
        ("edit_commit", "Остановись в `rebase -i`, измени коммит и продолжи.", 16),
        ("stash_workflow", "Спрячь изменения в stash и верни их обратно.", 10),
        ("reset_modes", "Покажи разницу `reset --soft`, `--mixed`, `--hard`.", 14),
    ],
    5: [
        ("clone_local", "Клонируй удалённый репозиторий в новую папку.", 8),
        ("add_remote", "Добавь `upstream` и проверь remotes через `git remote -v`.", 6),
        ("push_first", "Сделай первый push ветки в remote.", 9),
        ("fetch_merge", "Сделай `git fetch`, затем влей изменения вручную.", 12),
        ("pull_rebase", "Настрой `pull` через rebase и подтяни изменения.", 12),
        ("push_conflict", "Разрули non-fast-forward и успешно повтори push.", 15),
    ],
    6: [
        ("find_bisect", "Найди «плохой» коммит через `git bisect`.", 16),
        ("reflog_recovery", "Восстанови потерянный коммит с помощью `git reflog`.", 14),
        ("worktree", "Создай отдельный worktree для hotfix-ветки.", 10),
        ("inspect_objects", "Посмотри объекты через `git cat-file` и `git ls-tree`.", 14),
        ("custom_aliases_hooks", "Добавь alias и локальный hook для commit-msg.", 12),
        ("filter_branch", "Перепиши историю и удали чувствительный файл из прошлых коммитов.", 18),
    ],
    7: [
        ("setup_ignore", "Создай `.gitignore` и добавь `*.log`, `.env`, `__pycache__/`.", 8),
        ("ignore_node_modules", "Добавь правило `node_modules/` и проверь `git status`.", 7),
        ("untrack_cached", "Убери ранее отслеживаемый файл из индекса через `git rm --cached`.", 10),
        ("keep_empty_dir", "Сохрани пустую папку в Git через файл `.gitkeep`.", 7),
        ("ignore_exceptions", "Сделай исключение в `.gitignore` через `!` для одного файла.", 10),
    ],
    8: [
        ("create_lightweight_tag", "Создай lightweight тег `v0.1-lw` на текущем коммите.", 8),
        ("create_tag", "Создай аннотированный тег `v1.0` с сообщением.", 10),
        ("show_tag", "Покажи детали тега через `git show`.", 7),
        ("tag_old_commit", "Поставь тег на прошлый коммит по SHA.", 10),
        ("push_tags", "Подготовь релизный тег `v1.0` к публикации (в песочнице без сети проверяется наличие тега).", 10),
    ],
}

TASK_VALIDATORS = {
    "1.1": """\
import sys
import subprocess
from pathlib import Path

if not Path('.git').exists():
    print('Repository is not initialized')
    sys.exit(1)
subprocess.run(['git', 'rev-parse', '--git-dir'], check=True, capture_output=True, text=True)
print('OK: repository initialized')
""",
    "1.2": """\
import sys
import subprocess

msg = subprocess.run(['git', 'log', '-1', '--pretty=%s'], capture_output=True, text=True, check=False)
if msg.returncode != 0 or msg.stdout.strip() != 'Add hello':
    print('Expected last commit message: Add hello')
    sys.exit(1)

file_content = subprocess.run(['git', 'show', 'HEAD:hello.txt'], capture_output=True, text=True, check=False)
if file_content.returncode != 0 or file_content.stdout.strip() != 'Hello, Git!':
    print('hello.txt content mismatch in HEAD')
    sys.exit(1)
print('OK')
""",
    "1.3": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if ' M hello.txt' not in status:
    print('hello.txt should be modified and unstaged')
    sys.exit(1)
print('OK')
""",
    "1.4": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if ' M hello.txt' not in status:
    print('Expected modified but unstaged hello.txt. Use git add hello.txt then git restore --staged hello.txt (do not run git restore hello.txt).')
    sys.exit(1)
print('OK')
""",
    "1.5": """\
import sys
import subprocess

count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=False)
if count.returncode != 0 or int(count.stdout.strip()) < 2:
    print('Expected at least two commits')
    sys.exit(1)
msg = subprocess.run(['git', 'log', '-1', '--pretty=%s'], capture_output=True, text=True, check=False).stdout.strip()
if msg != 'Update hello':
    print('Expected latest commit message Update hello')
    sys.exit(1)
print('OK')
""",
    "1.6": """\
import sys
import subprocess

diff = subprocess.run(['git', 'diff'], capture_output=True, text=True, check=False).stdout
if 'Another line' not in diff:
    print('Expected Another line in git diff')
    sys.exit(1)
print('OK')
""",
    "1.7": """\
import sys
import subprocess

show = subprocess.run(['git', 'show', '--name-only', '--pretty=', 'HEAD'], capture_output=True, text=True, check=False).stdout
if 'config.txt' not in show:
    print('config.txt must be part of amended commit')
    sys.exit(1)
print('OK')
""",
    "1.8": """\
import sys
import subprocess

count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=False)
if count.returncode != 0 or int(count.stdout.strip()) < 2:
    print('Need at least two commits to inspect history')
    sys.exit(1)
print('OK')
""",
    "2.1": """\
import sys
import subprocess

branch = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, check=False).stdout.strip()
if branch != 'feature-x':
    print('Current branch should be feature-x')
    sys.exit(1)
print('OK')
""",
    "2.2": """\
import sys
import subprocess

show = subprocess.run(['git', 'show', '--name-only', '--pretty=', 'HEAD'], capture_output=True, text=True, check=False).stdout
if 'feature.txt' not in show:
    print('feature.txt should be committed in HEAD')
    sys.exit(1)
print('OK')
""",
    "2.3": """\
import sys
import subprocess
from pathlib import Path

branch = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, check=False).stdout.strip()
if branch != 'main':
    print('Switch back to main')
    sys.exit(1)
if Path('feature.txt').exists():
    print('feature.txt should not exist in main worktree')
    sys.exit(1)
print('OK')
""",
    "3.1": """\
import sys
import subprocess

parents = subprocess.run(['git', 'rev-list', '--parents', '-n', '1', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip().split()
if len(parents) != 2:
    print('Expected fast-forward without merge commit')
    sys.exit(1)
print('OK')
""",
    "3.2": """\
import sys
import subprocess

parents = subprocess.run(['git', 'rev-list', '--parents', '-n', '1', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip().split()
if len(parents) < 3:
    print('Expected merge commit with two parents')
    sys.exit(1)
print('OK')
""",
    "3.3": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if 'UU ' in status:
    print('Conflicts are not fully resolved')
    sys.exit(1)
print('OK')
""",
}


def _validator_by_slug(slug: str, external_id: str) -> str:
    if slug in {"list_branches"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True);sys.exit(0 if '*' in r.stdout else 1)"
    if slug in {"delete_branch"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True).stdout\nsys.exit(0 if 'feature-x' not in r else 1)"
    if slug in {"rename_branch"}:
        return "import subprocess, sys\nb=subprocess.run(['git','branch','--show-current'],capture_output=True,text=True).stdout.strip();sys.exit(0 if b and b!='main' else 1)"
    if slug in {"setup_ignore"}:
        return "from pathlib import Path\nimport sys\nc=Path('.gitignore').read_text(encoding='utf-8') if Path('.gitignore').exists() else ''\nsys.exit(0 if '*.log' in c and '__pycache__/' in c else 1)"
    if slug in {"create_tag", "push_tags"}:
        return "import subprocess, sys\nr=subprocess.run(['git','tag','-l','v1.0'],capture_output=True,text=True).stdout.strip();sys.exit(0 if r=='v1.0' else 1)"
    if slug in {"view_history", "branch_compare", "branch_from_commit", "track_remote_branch"}:
        return "import subprocess, sys\nr=subprocess.run(['git','rev-list','--count','HEAD'],capture_output=True,text=True,check=False)\nsys.exit(0 if r.returncode==0 and int((r.stdout or '0').strip() or 0)>=1 else 1)"
    if slug in {"switch_branch"}:
        return TASK_VALIDATORS["2.3"]
    if slug in {"commit_on_branch"}:
        return TASK_VALIDATORS["2.2"]
    if slug in {"create_branch"}:
        return TASK_VALIDATORS["2.1"]
    if slug in {"fast_forward_merge"}:
        return TASK_VALIDATORS["3.1"]
    if slug in {"no_ff_merge"}:
        return TASK_VALIDATORS["3.2"]
    if slug in {"resolve_conflict"}:
        return TASK_VALIDATORS["3.3"]
    if slug in {"abort_merge"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True).stdout\nsys.exit(0 if 'UU ' not in r else 1)"
    if slug in {"merge_tool", "octopus_merge", "squash_merge", "merge_vs_rebase", "cherry_pick_hotfix", "revert_merge"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)\nsys.exit(0 if r.returncode==0 else 1)"
    if slug in {"amend_message"}:
        return "import subprocess, sys\nm=subprocess.run(['git','log','-1','--pretty=%s'],capture_output=True,text=True).stdout.strip();sys.exit(0 if m else 1)"
    if slug in {"reorder_commits", "squash_commits", "drop_commit", "edit_commit", "rebase_onto"}:
        return "import subprocess, sys\nr=subprocess.run(['git','log','--oneline','-n','3'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"stash_workflow"}:
        return "import subprocess, sys\nr=subprocess.run(['git','stash','list'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"reset_modes"}:
        return "import subprocess, sys\nr=subprocess.run(['git','reflog','-n','5'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 and bool(r.stdout.strip()) else 1)"
    if slug in {"clone_local", "add_remote", "push_first", "fetch_merge", "pull_rebase", "push_conflict", "remote_prune"}:
        return "import subprocess, sys\nr=subprocess.run(['git','remote','-v'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"find_bisect", "reflog_recovery", "filter_branch", "worktree", "submodule", "inspect_objects", "custom_aliases_hooks"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"init_repo", "first_commit", "check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit"}:
        reverse_lookup = {
            "init_repo": "1.1",
            "first_commit": "1.2",
            "check_status": "1.3",
            "stage_unstage": "1.4",
            "commit_second": "1.5",
            "view_diff": "1.6",
            "amend_commit": "1.7",
        }
        mapped = reverse_lookup.get(slug)
        if mapped and mapped in TASK_VALIDATORS:
            return TASK_VALIDATORS[mapped]
    return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)\nsys.exit(0 if r.returncode==0 else 1)"


def validator_for(external_id: str, slug: str) -> str:
    return TASK_VALIDATORS.get(external_id) or _validator_by_slug(slug, external_id)


def task_metadata(level_number: int, slug: str, description: str) -> dict:
    requires = []
    if slug != "init_repo":
        requires.append("repo_initialized")
    if slug in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history"}:
        requires.append("hello_committed")
    if slug in {"commit_on_branch", "switch_branch", "list_branches", "delete_branch"}:
        requires.extend(["hello_committed", "feature_branch_exists"])
    validator_hints = ["Проверка опирается на состояние репозитория и историю коммитов."]
    if slug == "stage_unstage":
        validator_hints = [
            "Ожидается измененный `hello.txt` без staged-изменений.",
            "Подходит `git add hello.txt`, затем `git restore --staged hello.txt`.",
        ]
    return {
        "objective": description,
        "steps": [
            "Проверь стартовое состояние через git status --short.",
            "Выполни требуемые команды из условия.",
            "Подтверди результат через git status/git log и запусти проверку.",
        ],
        "expected_state": "Состояние репозитория соответствует формулировке задания.",
        "preconditions": requires,
        "validatorHints": validator_hints,
        "start": {
            "mode": "guided",
            "requires": requires,
            "assumes": [f"level_{level_number}_context"],
        },
        "recommendations": [
            "Начинай с git status, чтобы увидеть исходную точку.",
            "После каждого шага сверяйся с git log --oneline --graph.",
        ],
    }


def _zip_workspace(repo: Path) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in repo.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(repo))
    return f"base64zip:{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def build_start_repo_asset(slug: str) -> str | None:
    if slug not in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history"}:
        return None
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "gitplayground@example.local"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "GitPlayground Bot"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        (repo / "hello.txt").write_text("Hello, Git!\n", encoding="utf-8")
        subprocess.run(["git", "add", "hello.txt"], cwd=repo, check=False, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Add hello"], cwd=repo, check=False, capture_output=True, text=True)
        return _zip_workspace(repo)


def revision_payload(task: Task) -> dict:
    level_hint = {
        1: "Сфокусируйся на базовой механике хранилища и буферной зоны.",
        2: "Тренируй мгновенное переключение контекста через ветки.",
        3: "Отработай безопасную интеграцию изменений и разбор конфликтов.",
        4: "Научись аккуратно переписывать историю без потери контроля.",
        5: "Применяй распределенную модель: локально работаешь, в remote публикуешь.",
        6: "Используй диагностические и низкоуровневые инструменты Git.",
    }.get(task.level.number, "")
    objective = f"{task.description}\n\nКонтекст раздела: {level_hint}"
    metadata = task.metadata or {}
    steps = metadata.get(
        "steps",
        [
            "Проверь текущее состояние репозитория через git status --short.",
            "Выполни целевое действие из формулировки задачи.",
            "Подтверди результат через git status/git log и запусти проверку.",
        ],
    )
    expected_state = metadata.get(
        "expected_state",
        "Репозиторий находится в требуемом состоянии без лишних изменений.",
    )
    validator_notes = ""
    return {
        "objective": objective,
        "steps": steps,
        "expected_state": expected_state,
        "validator_notes": validator_notes,
        "schema_version": 1,
    }


class Command(BaseCommand):
    help = "Seed levels, theory blocks and task records with enriched GitMagic content."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_tasks = 0
        created_assets = 0
        for level_number, level_title, task_count in LEVELS:
            level_slug = f"level-{level_number}-{slugify(level_title)}"
            level, _ = Level.objects.update_or_create(
                number=level_number,
                defaults={
                    "title": level_title,
                    "slug": level_slug,
                    "description": f"Блок {level_number}: {level_title}",
                    "is_active": True,
                },
            )

            # DB data is source of truth: не перетираем уже отредактированную теорию.
            TheoryBlock.objects.get_or_create(
                level=level,
                defaults={
                    "title": f"Теория: {level_title}",
                    "content_md": THEORY_CONTENT[level_number],
                    "diagram_mermaid": LEVEL_DIAGRAMS[level_number],
                },
            )

            # Пересобираем github-задачи уровня детерминированно.
            Task.objects.filter(level=level, platform=Task.Platform.GITHUB).delete()
            for order, (slug, description, points) in enumerate(
                TASK_BLUEPRINTS.get(level_number, []), start=1
            ):
                level_hints = LEVEL_SECTION_HINTS.get(
                    level_number,
                    (
                        "Проверь текущее состояние через git status и выполни шаги задачи последовательно.",
                        "Сверь результат через git log --oneline и git status --short перед проверкой.",
                    ),
                )
                metadata = task_metadata(level_number, slug, description)
                defaults = {
                    "slug": slug,
                    "title": slug.replace("_", " ").title(),
                    "description": description,
                    "platform": Task.Platform.GITHUB,
                    "level": level,
                    "order": order,
                    "points": points,
                    "validator_cmd": "python validator.py",
                    "success_message": "Отлично! Задача решена.",
                    "metadata": metadata,
                }
                task = Task.objects.create(
                    external_id=f"gh-{level_number}.{order}",
                    **defaults,
                )
                revision, _ = TaskRevision.objects.update_or_create(
                    task=task,
                    version=1,
                    defaults={
                        "is_active": True,
                        **revision_payload(task),
                    },
                )
                TaskRevision.objects.filter(task=task).exclude(pk=revision.pk).update(is_active=False)
                start_repo_payload = build_start_repo_asset(slug)
                if start_repo_payload:
                    TaskAsset.objects.update_or_create(
                        task=task,
                        asset_type=TaskAsset.AssetType.START_REPO,
                        path="start-repo.zip",
                        defaults={
                            "sort_order": 1,
                            "content": start_repo_payload,
                        },
                    )
                else:
                    TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.START_REPO).delete()
                TaskAsset.objects.update_or_create(
                    task=task,
                    asset_type=TaskAsset.AssetType.VALIDATOR,
                    path="validator.py",
                    defaults={
                        "sort_order": 1,
                        "content": validator_for(task.external_id, slug),
                    },
                )
                TaskAsset.objects.update_or_create(
                    task=task,
                    asset_type=TaskAsset.AssetType.HINT,
                    path="hints/hint1.txt",
                    defaults={
                        "sort_order": 1,
                        "content": level_hints[0],
                    },
                )
                TaskAsset.objects.update_or_create(
                    task=task,
                    asset_type=TaskAsset.AssetType.HINT,
                    path="hints/hint2.txt",
                    defaults={
                        "sort_order": 2,
                        "content": level_hints[1],
                    },
                )
                created_tasks += 1
                created_assets += 3

        # Ачивки — глобальные определения; создаём один раз при сидировании, а не на каждый запрос профиля.
        from apps.achievements.services import bootstrap_default_achievements

        bootstrap_default_achievements()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(LEVELS)} levels, {created_tasks} tasks, {created_assets} assets."
            )
        )
