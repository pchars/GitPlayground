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
from apps.tasks.task_hints import TASK_HINTS
from apps.tasks.task_registry import LEVEL_TASK_POINTS, blueprints_for_level
from apps.tasks.task_validators import validator_for
from apps.tasks.theory_content import LEVEL_DIAGRAMS, LEVEL_SECTION_HINTS, THEORY_CONTENT


TASK_BLUEPRINTS = {level: blueprints_for_level(level) for level in LEVEL_TASK_POINTS}

LEVELS = [
    (0, "Терминал и знакомство с Git", 18),
    (1, "Основы Git", 12),
    (2, "Чистый репозиторий: .gitignore", 6),
    (3, "Ветвление", 9),
    (4, "Слияния и интеграция", 8),
    (5, "История и переписывание", 6),
    (6, "Удалённые репозитории", 7),
    (7, "Теги и релизы", 5),
    (8, "Диагностика и устройство Git", 13),
    (9, "Платформы и профессиональные практики", 13),
]


def task_metadata(level_number: int, slug: str, description: str) -> dict:
    requires = []
    if slug != "init_repo":
        requires.append("repo_initialized")
    if slug in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history", "grep_in_repo", "stage_tracked_only", "reset_head_unstage", "tree_list_root", "branch_without_checkout", "rescue_detached_head", "create_offline_bundle", "attach_git_note", "mr_feature_branch", "add_gitlab_ci_yaml"}:
        requires.append("hello_committed")
    if slug in {"export_format_patch", "git_mv_rename", "commit_signoff", "semantic_describe", "issue_close_message", "closes_issue_gitlab", "rev_parse_head_sha", "log_double_dot_range", "pickaxe_log_search", "merge_base_ready", "diff_cached_staged", "triple_dot_log_range"}:
        requires.append("hello_committed")
    if slug in {"readme_first", "gh_pages_branch", "jekyll_post_front_matter", "write_git_blob", "save_symbolic_head", "gitlab_md_issue_ref"}:
        requires.append("repo_initialized")
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
    if slug not in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history", "grep_in_repo", "stage_tracked_only", "reset_head_unstage"}:
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
        # Slugs are global; wipe all GitHub tasks before reordering levels.
        Task.objects.filter(platform=Task.Platform.GITHUB).delete()
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

            TheoryBlock.objects.update_or_create(
                level=level,
                defaults={
                    "title": f"Теория: {level_title}",
                    "content_md": THEORY_CONTENT[level_number],
                    "diagram_mermaid": LEVEL_DIAGRAMS[level_number],
                },
            )

            # Rebuild level tasks deterministically.
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

        # Achievements are global definitions; bootstrap once during seed, not per profile request.
        from apps.achievements.services import bootstrap_default_achievements

        bootstrap_default_achievements()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(LEVELS)} levels, {created_tasks} tasks, {created_assets} assets."
            )
        )
