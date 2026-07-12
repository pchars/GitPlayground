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

import shutil

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, tag

from apps.core.services import get_or_create_active_session, run_command, stop_session, validate_task
from apps.core.services import sandbox_ops
from apps.core.services.sandbox_ops import SANDBOX_ROOT
from apps.progress.models import TaskAttempt
from apps.tasks.models import Task


# Intended solution per task slug. Each value is the ordered list of commands a
# learner types into the sandbox terminal. An empty list means the seeded start
# state already satisfies the validator (exploration/read-only tasks).
SOLUTIONS: dict[str, list[str]] = {
    # Level 0 — terminal sandbox
    "sandbox_pwd": ["pwd"],
    "sandbox_ls": ["ls"],
    "sandbox_whoami": ["whoami"],
    "sandbox_mkdir": ["mkdir -p practice"],
    "sandbox_touch": ["mkdir -p practice", "touch practice/notes.txt"],
    "sandbox_echo_write": ["mkdir -p practice", "echo GitPlayground > practice/notes.txt"],
    "sandbox_cat": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "cat practice/notes.txt",
    ],
    "sandbox_echo_append": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "echo sandbox >> practice/notes.txt",
    ],
    "sandbox_type_empty": ["mkdir -p practice", "type nul > practice/blank.txt"],
    "sandbox_head": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "head -n 1 practice/notes.txt",
    ],
    "sandbox_tail": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "echo sandbox >> practice/notes.txt",
        "tail -n 1 practice/notes.txt",
    ],
    "sandbox_wc": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "echo sandbox >> practice/notes.txt",
        "wc -l practice/notes.txt",
    ],
    "sandbox_cp": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "cp practice/notes.txt practice/copy.txt",
    ],
    "sandbox_mv": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "cp practice/notes.txt practice/copy.txt",
        "mv practice/copy.txt practice/backup.txt",
    ],
    "sandbox_find": [
        "mkdir -p practice",
        "echo GitPlayground > practice/notes.txt",
        "find practice",
    ],
    "sandbox_rm": [
        "mkdir -p practice",
        "type nul > practice/blank.txt",
        "rm practice/blank.txt",
    ],
    "sandbox_nano": ["nano practice/diary.txt"],
    "sandbox_clear": ["clear"],
    # Level 1 — basics
    "init_repo": ["git init"],
    "first_commit": [
        'echo "Hello, Git!" > hello.txt',
        "git add hello.txt",
        'git commit -m "Add hello"',
    ],
    "check_status": [
        'echo "review later" >> hello.txt',
        "git status",
    ],
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
    "view_history": ["git log --oneline"],
    "grep_in_repo": [
        "git grep Git > grep-hit.txt",
    ],
    "stage_tracked_only": [
        'echo "tracked-only" >> hello.txt',
        'echo "temp" > scratch.txt',
        "git add -u",
        'git commit -m "Only tracked files"',
    ],
    "reset_head_unstage": [
        'echo "reset head demo" >> hello.txt',
        "git add hello.txt",
        "git reset HEAD hello.txt",
    ],
    # Level 2 — repository hygiene
    "setup_ignore": [
        "echo *.log > .gitignore",
        "echo .env >> .gitignore",
        "echo __pycache__/ >> .gitignore",
    ],
    "ignore_node_modules": ['echo "node_modules/" >> .gitignore'],
    "untrack_cached": [
        'echo "secrets.env" >> .gitignore',
        "git rm --cached secrets.env",
    ],
    "keep_empty_dir": [
        "mkdir -p notes",
        "touch notes/.gitkeep",
        "git add notes/.gitkeep",
        'git commit -m "Keep notes directory"',
    ],
    "ignore_exceptions": [
        'echo "*.log" > .gitignore',
        'echo "!important.log" >> .gitignore',
    ],
    "clean_untracked": [
        "echo garbage > garbage.tmp",
        "git clean -n",
        "git clean -f",
    ],
    # Level 3 — branching
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
    "branch_without_checkout": [
        "git branch sidecar",
        "echo main > active-branch.txt",
    ],
    "rescue_detached_head": [
        "git checkout --detach",
        "git checkout -b rescue-tip",
        "echo rescue-tip > rescue-branch.txt",
    ],
    # Level 4 — merges and integration
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
    # Level 5 — history rewriting
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
    # Level 6 — remotes
    "clone_local": [],
    "add_remote": [],
    "push_first": [],
    "fetch_merge": [],
    "pull_rebase": [],
    "push_conflict": [],
    "create_offline_bundle": ["git bundle create repo.bundle HEAD main"],
    # Level 8 — diagnostics and internals
    "find_bisect": [],
    "reflog_recovery": [],
    "worktree": [],
    "inspect_objects": [],
    "custom_aliases_hooks": [],
    "filter_branch": [],
    # Level 7 — tagging
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
    # Level 9 — platforms & pro practices
    "export_format_patch": ["git format-patch -1 HEAD"],
    "git_mv_rename": [
        "git mv hello.txt readme.txt",
        'git commit -m "Rename hello to readme"',
    ],
    "commit_signoff": [
        'echo "signed" >> hello.txt',
        "git add hello.txt",
        'git commit -s -m "Update with sign-off"',
    ],
    "semantic_describe": [
        'git tag -a v1.0.0 -m "Release 1.0.0"',
        "git describe --tags",
    ],
    "readme_first": [
        'echo "# GitPlayground Demo" > README.md',
        "git add README.md",
        'git commit -m "Add README"',
    ],
    "issue_close_message": [
        'echo "fix" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Fix typo, Fixes #42"',
    ],
    "gh_pages_branch": [
        "git checkout -b gh-pages",
        'echo "<h1>Project page</h1>" > index.html',
        "git add index.html",
        'git commit -m "Add GitHub Pages stub"',
    ],
    "jekyll_post_front_matter": [
        "mkdir _posts",
        "echo --- > _posts/welcome.md",
        "echo title: Welcome >> _posts/welcome.md",
        "echo layout: post >> _posts/welcome.md",
        "echo --- >> _posts/welcome.md",
        "echo Hello Jekyll >> _posts/welcome.md",
        "git add _posts/welcome.md",
        'git commit -m "Add Jekyll post"',
    ],
    "write_git_blob": [
        "echo api > api.txt",
        "git hash-object -w api.txt",
    ],
    "save_symbolic_head": [
        "git checkout -b internals-demo",
        "echo refs/heads/internals-demo > head-ref.txt",
    ],
    "tree_list_root": ["echo hello.txt > tree-list.txt"],
    "attach_git_note": [
        'git notes add -m "reviewed"',
        "echo reviewed > note-check.txt",
    ],
    "rev_parse_head_sha": [
        "echo main > current-branch.txt",
    ],
    "log_double_dot_range": [
        "git checkout -b explore-range",
        'echo "range" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Commit for double-dot range"',
        "echo ok > range-done.txt",
    ],
    "pickaxe_log_search": [
        'echo PROGIT_FIND >> hello.txt',
        "git add hello.txt",
        'git commit -m "Add pickaxe marker"',
        "echo ok > pickaxe-done.txt",
    ],
    "triple_dot_log_range": [
        "git checkout -b triple-explore",
        'echo "triple" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Commit for triple-dot range"',
        "echo ok > triple-done.txt",
    ],
    "diff_cached_staged": [
        'echo "staged line" >> hello.txt',
        "git add hello.txt",
        "echo ok > staged-ready.txt",
    ],
    "merge_base_ready": [
        "git checkout -b prof-feature",
        'echo "prof" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Prof feature commit"',
        "echo ok > merge-base-done.txt",
    ],
    "mr_feature_branch": [
        "git checkout -b awesome-feature",
        "echo update >> hello.txt",
        "git add hello.txt",
        'git commit -m "Feature for MR"',
        "echo awesome-feature > mr-branch.txt",
    ],
    "add_gitlab_ci_yaml": [
        "echo test: > .gitlab-ci.yml",
        "echo   script: >> .gitlab-ci.yml",
        "echo     - echo ok >> .gitlab-ci.yml",
        "git add .gitlab-ci.yml",
        'git commit -m "Add GitLab CI config"',
    ],
    "closes_issue_gitlab": [
        'echo "gitlab" >> hello.txt',
        "git add hello.txt",
        'git commit -m "Docs update, Closes #7"',
    ],
    "gitlab_md_issue_ref": [
        'echo "See issue #3 for details" > notes.md',
        "git add notes.md",
        'git commit -m "Add GLFM issue reference"',
    ],
}


@tag("slow")
class TaskSolvabilityTests(TestCase):
    """Every seeded task must pass via its intended solution (tag slow: ~90s)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._orig_engine = sandbox_ops.SANDBOX_ENGINE
        sandbox_ops.SANDBOX_ENGINE = "local"

    @classmethod
    def tearDownClass(cls):
        sandbox_ops.SANDBOX_ENGINE = cls._orig_engine
        if SANDBOX_ROOT.exists():
            for child in SANDBOX_ROOT.iterdir():
                shutil.rmtree(child, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        call_command("seed_initial_data")
        cls.solver = User.objects.create_user(username="golden_solver", password="pw")

    def _solve(self, task: Task) -> TaskAttempt:
        session = get_or_create_active_session(self.solver, task)
        for command in SOLUTIONS[task.slug]:
            result = run_command(session, command)
            self.assertNotEqual(
                result.return_code,
                126,
                msg=f"[{task.external_id} {task.slug}] command blocked by policy: {command!r}",
            )
        attempt = validate_task(self.solver, task, session)
        stop_session(session)
        return attempt

    def test_every_seeded_task_is_solvable(self):
        tasks = list(Task.objects.select_related("level").order_by("level__number", "order"))
        self.assertGreater(len(tasks), 0, "Seed produced no tasks")

        for task in tasks:
            with self.subTest(task=task.external_id, slug=task.slug):
                attempt = self._solve(task)
                self.assertEqual(
                    attempt.verdict,
                    TaskAttempt.Verdict.PASSED,
                    msg=(
                        f"[{task.external_id} {task.slug}] expected PASSED but got "
                        f"{attempt.verdict}. Diagnostics:\n{attempt.diagnostics}"
                    ),
                )
