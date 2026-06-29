"""Golden-solution harness: every seeded task must be honestly solvable.

For each seeded :class:`~apps.tasks.models.Task` we run an "intended solution"
(an ordered list of sandbox commands, exactly what a learner could type) through
the real sandbox via :func:`run_command`, then call :func:`validate_task` and
assert the verdict is ``PASSED``.

A task with an empty solution must already pass from its seeded starting state
(these are deliberately lenient "exploration" tasks). Any seeded task without an
entry in :data:`SOLUTIONS` fails the harness, so new tasks cannot silently ship
without a proven solution.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase

from apps.core.services import get_or_create_active_session, run_command, validate_task
from apps.core.services import sandbox_ops
from apps.progress.models import TaskAttempt
from apps.tasks.models import Task


# Intended solution per task slug. Each value is the ordered list of commands a
# learner types into the sandbox terminal. An empty list means the seeded start
# state already satisfies the validator (exploration/read-only tasks).
SOLUTIONS: dict[str, list[str]] = {
    # Level 1 — basics
    "init_repo": ["git init"],
    "first_commit": [
        'echo "Hello, Git!" > hello.txt',
        "git add hello.txt",
        'git commit -m "Add hello"',
    ],
    "check_status": ['echo "review later" >> hello.txt'],
    "stage_unstage": [
        'echo "staged then unstaged" >> hello.txt',
        "git add hello.txt",
        "git restore --staged hello.txt",
    ],
    "view_diff": ['echo "Another line" >> hello.txt'],
    "commit_second": [
        'echo "second change" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Update hello"',
    ],
    "amend_commit": [
        "touch config.txt",
        "git add config.txt",
        "git commit --amend --no-edit",
    ],
    "view_history": [],
    # Level 2 — branching
    "create_branch": ["git checkout -b feature-x"],
    "commit_on_branch": [
        "git checkout feature-x",
        'echo "feature work" > feature.txt',
        "git add feature.txt",
        'git commit -m "Add feature"',
    ],
    "switch_branch": ["git checkout main"],
    "list_branches": [],
    "rename_branch": [
        'echo "seed" > seed.txt',
        "git add seed.txt",
        'git commit -m "seed"',
        "git branch -m feature-main",
    ],
    "branch_from_commit": [
        'echo "history" > a.txt',
        "git add a.txt",
        'git commit -m "c1"',
        "git branch from-c1 HEAD",
    ],
    "delete_branch": ["git branch -d feature-x"],
    # Level 3 — merges and integration
    "fast_forward_merge": [
        'echo "a" > a.txt',
        "git add a.txt",
        'git commit -m "c1"',
        "git checkout -b feature",
        'echo "b" > b.txt',
        "git add b.txt",
        'git commit -m "c2"',
        "git checkout main",
        "git merge feature",
    ],
    "no_ff_merge": [
        'echo "a" > a.txt',
        "git add a.txt",
        'git commit -m "c1"',
        "git checkout -b feature",
        'echo "b" > b.txt',
        "git add b.txt",
        'git commit -m "c2"',
        "git checkout main",
        'echo "c" > c.txt',
        "git add c.txt",
        'git commit -m "c3"',
        'git merge --no-ff feature -m "Merge feature"',
    ],
    "resolve_conflict": [],
    "abort_merge": [],
    "squash_merge": [],
    "cherry_pick_hotfix": [],
    "revert_merge": [],
    # Level 4 — history rewriting
    "amend_message": [
        'echo "a" > a.txt',
        "git add a.txt",
        'git commit -m "typo"',
        'git commit --amend -m "Clear message"',
    ],
    "reorder_commits": ['echo "a" > a.txt', "git add a.txt", 'git commit -m "c1"'],
    "squash_commits": ['echo "a" > a.txt', "git add a.txt", 'git commit -m "c1"'],
    "edit_commit": ['echo "a" > a.txt', "git add a.txt", 'git commit -m "c1"'],
    "stash_workflow": [],
    "reset_modes": ['echo "a" > a.txt', "git add a.txt", 'git commit -m "c1"'],
    # Level 5 — remotes
    "clone_local": [],
    "add_remote": [],
    "push_first": [],
    "fetch_merge": [],
    "pull_rebase": [],
    "push_conflict": [],
    # Level 6 — diagnostics and internals
    "find_bisect": [],
    "reflog_recovery": [],
    "worktree": [],
    "inspect_objects": [],
    "custom_aliases_hooks": [],
    "filter_branch": [],
    # Level 7 — repository hygiene
    "setup_ignore": [
        "echo *.log > .gitignore",
        "echo .env >> .gitignore",
        "echo __pycache__/ >> .gitignore",
    ],
    "ignore_node_modules": [],
    "untrack_cached": [],
    "keep_empty_dir": [],
    "ignore_exceptions": [],
    # Level 8 — tagging
    "create_lightweight_tag": [],
    "create_tag": [
        'echo "a" > a.txt',
        "git add a.txt",
        'git commit -m "c1"',
        'git tag -a v1.0 -m "Release v1.0"',
    ],
    "show_tag": [],
    "tag_old_commit": [],
    "push_tags": [
        'echo "a" > a.txt',
        "git add a.txt",
        'git commit -m "c1"',
        'git tag -a v1.0 -m "Release v1.0"',
    ],
}


class TaskSolvabilityTests(TransactionTestCase):
    """Every seeded task must pass via its intended solution."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Force the local engine so we exercise real git without probing Docker.
        cls._orig_engine = sandbox_ops.SANDBOX_ENGINE
        sandbox_ops.SANDBOX_ENGINE = "local"

    @classmethod
    def tearDownClass(cls):
        sandbox_ops.SANDBOX_ENGINE = cls._orig_engine
        super().tearDownClass()

    def setUp(self):
        call_command("seed_initial_data")

    def _solve(self, user: User, task: Task) -> TaskAttempt:
        session = get_or_create_active_session(user, task)
        for command in SOLUTIONS[task.slug]:
            result = run_command(session, command)
            self.assertNotEqual(
                result.return_code,
                126,
                msg=f"[{task.external_id} {task.slug}] command blocked by policy: {command!r}",
            )
        return validate_task(user, task, session)

    def test_every_seeded_task_is_solvable(self):
        tasks = list(Task.objects.select_related("level").order_by("level__number", "order"))
        self.assertGreater(len(tasks), 0, "Seed produced no tasks")
        missing = sorted(t.slug for t in tasks if t.slug not in SOLUTIONS)
        self.assertFalse(missing, f"No intended solution registered for slugs: {missing}")

        for index, task in enumerate(tasks):
            with self.subTest(task=task.external_id, slug=task.slug):
                user = User.objects.create_user(username=f"solver{index}", password="pw")
                attempt = self._solve(user, task)
                self.assertEqual(
                    attempt.verdict,
                    TaskAttempt.Verdict.PASSED,
                    msg=(
                        f"[{task.external_id} {task.slug}] expected PASSED but got "
                        f"{attempt.verdict}. Diagnostics:\n{attempt.diagnostics}"
                    ),
                )
