"""Quiz difficulty calibrated to theory levels (0 easiest … 9 hardest).

Questions are tagged with a theory level from the course arc, then mapped to the
UI buckets easy / medium / hard:

- levels 0–3 → easy
- levels 4–6 → medium
- levels 7–9 → hard
"""

from __future__ import annotations

MAX_THEORY_LEVEL = 9


def difficulty_from_theory_level(level: int) -> str:
    level = max(0, min(MAX_THEORY_LEVEL, int(level)))
    if level <= 3:
        return "easy"
    if level <= 6:
        return "medium"
    return "hard"


# Longer / more specific markers must come first (first match wins).
_COMMAND_LEVEL_RULES: tuple[tuple[str, int], ...] = (
    # Level 9 — platforms / professional workflow
    ("format-patch", 9),
    ("git am", 9),
    ("request-pull", 9),
    ("send-email", 9),
    ("signoff", 9),
    ("--signoff", 9),
    # Level 8 — diagnostics / plumbing
    ("hash-object", 8),
    ("write-tree", 8),
    ("commit-tree", 8),
    ("cat-file", 8),
    ("update-ref", 8),
    ("symbolic-ref", 8),
    ("for-each-ref", 8),
    ("ls-tree", 8),
    ("rev-parse", 8),
    ("range-diff", 8),
    ("filter-repo", 8),
    ("filter-branch", 8),
    ("sparse-checkout", 8),
    ("update-index", 8),
    ("interpret-trailers", 8),
    ("verify-commit", 8),
    ("verify-tag", 8),
    ("notes add", 8),
    ("notes show", 8),
    ("git notes", 8),
    ("worktree", 8),
    ("submodule", 8),
    ("bisect", 8),
    ("reflog", 8),
    ("replace", 8),
    ("maintenance", 8),
    ("rerere", 8),
    ("log -S", 8),
    ("log --grep", 8),
    ("show-ref", 8),
    # Level 7 — tags
    ("describe", 7),
    ("tag -a", 7),
    ("tag -d", 7),
    ("tag -l", 7),
    ("push --tags", 7),
    ("git tag", 7),
    # Level 6 — remotes
    ("force-with-lease", 6),
    ("push --push-option", 6),
    ("push --delete", 6),
    ("push --set-upstream", 6),
    ("push -u", 6),
    ("push origin", 6),
    ("fetch --prune", 6),
    ("fetch origin", 6),
    ("pull --rebase", 6),
    ("pull --ff", 6),
    ("pull --no-rebase", 6),
    ("pull origin", 6),
    ("remote show", 6),
    ("remote remove", 6),
    ("remote add", 6),
    ("remote -v", 6),
    ("clone --depth", 6),
    ("git bundle", 6),
    ("bundle", 6),
    ("git clone", 6),
    ("git remote", 6),
    ("git fetch", 6),
    ("git push", 6),
    ("git pull", 6),
    # Level 5 — history rewrite
    ("rebase --rebase-merges", 5),
    ("rebase --onto", 5),
    ("rebase --root", 5),
    ("rebase --autosquash", 5),
    ("rebase --skip", 5),
    ("rebase --keep-empty", 5),
    ("commit --fixup", 5),
    ("commit --squash", 5),
    ("commit --amend", 5),
    ("reset --soft", 5),
    ("reset --mixed", 5),
    ("reset --hard", 5),
    ("stash -u", 5),
    ("stash pop", 5),
    ("stash apply", 5),
    ("stash list", 5),
    ("stash drop", 5),
    ("git rebase", 5),
    ("git stash", 5),
    ("amend", 5),
    ("squash", 5),
    # Level 4 — merges
    ("cherry-pick --no-commit", 4),
    ("merge --verify-signatures", 4),
    ("merge --no-commit", 4),
    ("merge --signoff", 4),
    ("merge -X", 4),
    ("merge --", 4),
    ("cherry-pick", 4),
    ("git revert", 4),
    ("git merge", 4),
    ("abort", 4),
    ("continue", 4),
    # Level 3 — branches
    ("checkout --orphan", 3),
    ("checkout --track", 3),
    ("switch --detach", 3),
    ("switch -c", 3),
    ("checkout -b", 3),
    ("branch --show-current", 3),
    ("branch --set-upstream", 3),
    ("branch --no-merged", 3),
    ("branch --merged", 3),
    ("branch -m", 3),
    ("branch -D", 3),
    ("branch -d", 3),
    ("git switch", 3),
    ("git checkout", 3),
    ("git branch", 3),
    # Level 2 — ignore / clean
    ("rm --cached", 2),
    ("git clean", 2),
    ("gitignore", 2),
    # Level 1 — fundamentals
    ("diff --staged", 1),
    ("diff --cached", 1),
    ("diff --name-only", 1),
    ("diff --check", 1),
    ("diff --color-moved", 1),
    ("diff HEAD", 1),
    ("log --oneline", 1),
    ("log --graph", 1),
    ("log --first-parent", 1),
    ("log --decorate", 1),
    ("log --reverse", 1),
    ("log --stat", 1),
    ("log -p", 1),
    ("restore --staged", 1),
    ("reset HEAD", 1),
    ("commit -a", 1),
    ("commit --allow-empty", 1),
    ("add -p", 1),
    ("git restore", 1),
    ("git reset", 1),
    ("git grep", 1),
    ("git show", 1),
    ("git diff", 1),
    ("git log", 1),
    ("git commit", 1),
    ("git status", 1),
    ("git add", 1),
    ("git init", 1),
    ("git mv", 1),
    ("git rm", 1),
    ("git blame", 1),
    ("git help", 1),
    ("git version", 1),
    ("git config", 1),
    ("git shortlog", 1),
    ("git archive", 1),
    ("git apply", 1),
    ("show --name-only", 1),
)


# Concept markers keyed by theory level (max matching level wins).
_CONCEPT_LEVEL_MARKERS: dict[int, tuple[str, ...]] = {
    0: (
        "терминал",
        "командная строка",
        "shell",
        "pwd",
        "whoami",
    ),
    1: (
        "три состоян",
        "три основных состоян",
        "staging area",
        "stage area",
        "индекс",
        "снимк",
        "snapshots",
        "modified",
        "staged",
        "committed",
        "зафиксирован",
        "изменён",
        "изменен",
        "рабоч",
        "working directory",
        "git directory",
        "sha-1",
        "целостност",
        "только добавляет данные",
        "git add",
        "git status",
        "git init",
        "git commit",
        "git log",
        "git diff",
        "git restore",
        "git grep",
    ),
    2: (
        "gitignore",
        ".gitignore",
        "untracked",
        "git clean",
        "gitkeep",
        "rm --cached",
    ),
    3: (
        "ветк",
        "topic branch",
        "detached head",
        "tracking branch",
        "remote-tracking",
        "git branch",
        "git switch",
        "git checkout",
        "ветки полностью локальны",
    ),
    4: (
        "fast-forward",
        "merge conflict markers",
        "<<<<<<<",
        "three-way merge",
        "merge-base",
        "no-ff",
        "ours",
        "theirs",
        "конфликт",
        "cherry-pick",
        "git merge",
        "git revert",
    ),
    5: (
        "rebase",
        "reset --soft",
        "reset --mixed",
        "reset --hard",
        "три дерева",
        "stash",
        "amend",
        "squash",
        "interactive rebase",
    ),
    6: (
        "origin",
        "upstream",
        "clone",
        "fetch",
        "pull = fetch",
        "bare repository",
        "локальн",
        "офлайн",
        "force-with-lease",
        "force push",
        "shallow clone",
        "git remote",
        "git push",
        "git pull",
        "git fetch",
        "bundle",
    ),
    7: (
        "annotated tag",
        "lightweight tag",
        "semantic version",
        "semver",
        "git tag",
        "git describe",
    ),
    8: (
        "plumbing",
        "porcelain",
        "blob",
        "tree-объект",
        "commit-объект",
        "hash-object",
        "write-tree",
        "commit-tree",
        "cat-file",
        "packfiles",
        "pack file",
        "packfile",
        "object database",
        ".git/objects",
        ".git/refs",
        "symbolic ref",
        "update-ref",
        "for-each-ref",
        "replace",
        "filter-repo",
        "fsck",
        "git gc",
        "range-diff",
        "bisect",
        "reflog",
        "rerere",
        "worktree",
        "submodule",
        "sparse-checkout",
        "git notes",
        "notes add",
        "ls-tree",
        "rev-parse",
        "hook",
        "pre-commit",
        "pre-push",
        "server-side hook",
        "alias",
    ),
    9: (
        "pull request",
        "merge request",
        "github actions",
        "github pages",
        "gitlab ci",
        "format-patch",
        "git am",
        "signed-off",
        "sign-off",
        "dco",
        "integration-manager",
        "dictator",
        "workflow",
        "ci",
        "jekyll",
        "gitattributes",
        "autocrlf",
        "gpg",
        "signed commit",
        "публичн",
        "shared-вет",
    ),
}


def command_theory_level(cmd: str) -> int:
    lowered = (cmd or "").strip().lower()
    for marker, level in _COMMAND_LEVEL_RULES:
        if marker.lower() in lowered:
            return level
    return 1


def concept_theory_level(prompt: str, correct: str) -> int:
    text = f"{prompt} {correct}".lower()
    best = 1
    for level, markers in _CONCEPT_LEVEL_MARKERS.items():
        if any(marker in text for marker in markers):
            best = max(best, level)
    return best


def classify_command_difficulty(cmd: str) -> str:
    """Difficulty for a question about a specific git command."""
    return difficulty_from_theory_level(command_theory_level(cmd))


def classify_concept_difficulty(prompt: str, correct: str) -> str:
    """Difficulty for a concept question from prompt and correct answer."""
    return difficulty_from_theory_level(concept_theory_level(prompt, correct))


def classify_question_difficulty(*, prompt: str, correct: str, cmd: str | None = None) -> str:
    if cmd is not None:
        return classify_command_difficulty(cmd)
    return classify_concept_difficulty(prompt, correct)
