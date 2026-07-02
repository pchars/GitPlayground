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
from apps.tasks.task_descriptions import TASK_CONDITIONS
from apps.tasks.task_hints import TASK_HINTS
from apps.tasks.theory_content import LEVEL_DIAGRAMS, LEVEL_SECTION_HINTS, THEORY_CONTENT


def _task_blueprints(specs: list[tuple[str, int]]) -> list[tuple[str, str, int]]:
    return [(slug, TASK_CONDITIONS[slug], points) for slug, points in specs]


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
    1: _task_blueprints(
        [
            ("init_repo", 6),
            ("first_commit", 10),
            ("check_status", 6),
            ("stage_unstage", 8),
            ("view_diff", 6),
            ("commit_second", 10),
            ("amend_commit", 12),
            ("view_history", 6),
        ]
    ),
    2: _task_blueprints(
        [
            ("create_branch", 8),
            ("commit_on_branch", 10),
            ("switch_branch", 6),
            ("list_branches", 5),
            ("rename_branch", 8),
            ("branch_from_commit", 12),
            ("delete_branch", 7),
        ]
    ),
    3: _task_blueprints(
        [
            ("fast_forward_merge", 8),
            ("no_ff_merge", 12),
            ("resolve_conflict", 18),
            ("abort_merge", 10),
            ("squash_merge", 14),
            ("cherry_pick_hotfix", 12),
            ("revert_merge", 14),
        ]
    ),
    4: _task_blueprints(
        [
            ("amend_message", 8),
            ("reorder_commits", 14),
            ("squash_commits", 14),
            ("edit_commit", 16),
            ("stash_workflow", 10),
            ("reset_modes", 14),
        ]
    ),
    5: _task_blueprints(
        [
            ("clone_local", 8),
            ("add_remote", 6),
            ("push_first", 9),
            ("fetch_merge", 12),
            ("pull_rebase", 12),
            ("push_conflict", 15),
        ]
    ),
    6: _task_blueprints(
        [
            ("find_bisect", 16),
            ("reflog_recovery", 14),
            ("worktree", 10),
            ("inspect_objects", 14),
            ("custom_aliases_hooks", 12),
            ("filter_branch", 18),
        ]
    ),
    7: _task_blueprints(
        [
            ("setup_ignore", 8),
            ("ignore_node_modules", 7),
            ("untrack_cached", 10),
            ("keep_empty_dir", 7),
            ("ignore_exceptions", 10),
        ]
    ),
    8: _task_blueprints(
        [
            ("create_lightweight_tag", 8),
            ("create_tag", 10),
            ("show_tag", 7),
            ("tag_old_commit", 10),
            ("push_tags", 10),
        ]
    ),
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
        "preconditions": requires,
        "validatorHints": validator_hints,
        "start": {
            "mode": "guided",
            "requires": requires,
        },
    }


def revision_payload(task: Task) -> dict:
    return {
        "objective": task.description,
        "steps": [],
        "expected_state": "",
        "validator_notes": "",
        "schema_version": 1,
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
                task_hints = TASK_HINTS.get(slug) or LEVEL_SECTION_HINTS.get(
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
                        "content": task_hints[0],
                    },
                )
                TaskAsset.objects.update_or_create(
                    task=task,
                    asset_type=TaskAsset.AssetType.HINT,
                    path="hints/hint2.txt",
                    defaults={
                        "sort_order": 2,
                        "content": task_hints[1],
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
