"""Extract task-relevant theory from the level THEORY_CONTENT (single source of truth)."""

from __future__ import annotations

import re

from django.utils.text import slugify

# Heading titles (after ## ) in THEORY_CONTENT / level0 theory → task slugs that show them.
# Titles must match the level markdown exactly (without the leading ## ).
TASK_THEORY_HEADINGS: dict[str, tuple[str, ...]] = {
    # Level 0
    "sandbox_pwd": ("`pwd` — текущая папка", "Что такое терминал"),
    "sandbox_ls": ("`ls` — список файлов", "Что такое терминал"),
    "sandbox_whoami": ("`whoami` — кто вы в песочнице",),
    "sandbox_mkdir": ("`mkdir` — создать каталог",),
    "sandbox_touch": ("`touch` — создать пустой файл",),
    "sandbox_echo_write": ("`echo` и перенаправление в файл",),
    "sandbox_cat": ("`cat` — прочитать файл",),
    "sandbox_echo_append": ("`echo` и перенаправление в файл",),
    "sandbox_type_empty": ("`type nul >` — пустой файл",),
    "sandbox_head": ("`head` и `tail` — края файла",),
    "sandbox_tail": ("`head` и `tail` — края файла",),
    "sandbox_wc": ("`wc -l` — число строк",),
    "sandbox_cp": ("`cp` и `mv` — копия и переименование",),
    "sandbox_mv": ("`cp` и `mv` — копия и переименование",),
    "sandbox_find": ("`find` — обход каталога",),
    "sandbox_rm": ("`rm` — удалить файл",),
    "sandbox_nano": ("`nano` / `edit` — редактор",),
    "sandbox_clear": ("`clear` — очистить экран",),
    # Level 1
    "init_repo": ("Три зоны Git", "`git init` — создать репозиторий"),
    "first_commit": (
        "`git add` — положить изменения в индекс",
        "`git commit` — зафиксировать снимок",
    ),
    "check_status": ("`git status` — панель приборов",),
    "stage_unstage": (
        "`git add` — положить изменения в индекс",
        "`git restore` — отменить staging (и правки)",
    ),
    "view_diff": ("`git diff` — посмотреть отличия",),
    "commit_second": ("`git commit` — зафиксировать снимок", "`git log` — история коммитов"),
    "amend_commit": ("`git commit` — зафиксировать снимок",),
    "view_history": ("`git log` — история коммитов",),
    "grep_in_repo": ("`git grep` — поиск по отслеживаемым файлам",),
    "stage_tracked_only": ("`git add` — положить изменения в индекс",),
    "reset_head_unstage": ("`git reset HEAD` — снять с индекса (классика)",),
    "diff_cached_staged": ("`git diff` — посмотреть отличия",),
    # Level 2
    "setup_ignore": ("Как работает `.gitignore`",),
    "ignore_node_modules": ("Как работает `.gitignore`",),
    "untrack_cached": ("Файл уже в Git, но его надо игнорировать",),
    "keep_empty_dir": ("Пустые папки и `.gitkeep`",),
    "ignore_exceptions": ("Как работает `.gitignore`",),
    "clean_untracked": ("`git clean` — убрать untracked файлы",),
    # Level 3
    "create_branch": ("`git branch` — список и управление", "`git checkout` — классический способ"),
    "commit_on_branch": ("Topic-ветки (привычка команд)",),
    "switch_branch": ("`git switch` — современное переключение", "`git checkout` — классический способ"),
    "list_branches": ("`git branch` — список и управление",),
    "rename_branch": ("`git branch` — список и управление",),
    "branch_from_commit": ("`git branch` — список и управление",),
    "delete_branch": ("`git branch` — список и управление",),
    "branch_without_checkout": ("`git branch` — список и управление",),
    "rescue_detached_head": ("Detached HEAD — что это",),
}

_H2_SPLIT = re.compile(r"(?m)^(##\s+.+)$")


def heading_anchor(title: str) -> str:
    plain = re.sub(r"[*_`]+", "", title).strip()
    return slugify(plain, allow_unicode=True)


def iter_h2_sections(content_md: str) -> list[tuple[str, str]]:
    """Return [(heading_title_without_hashes, section_markdown_including_heading), ...]."""
    text = content_md or ""
    parts = _H2_SPLIT.split(text)
    if len(parts) < 2:
        return []
    sections: list[tuple[str, str]] = []
    # parts[0] is preamble before first ##
    idx = 1
    while idx + 1 < len(parts):
        heading_line = parts[idx].strip()
        body = parts[idx + 1]
        title = re.sub(r"^##\s+", "", heading_line).strip()
        sections.append((title, f"## {title}\n{body}".rstrip() + "\n"))
        idx += 2
    return sections


def extract_sections_by_titles(content_md: str, titles: tuple[str, ...]) -> str:
    if not titles:
        return ""
    wanted = {t.strip() for t in titles}
    chunks: list[str] = []
    seen: set[str] = set()
    for title, block in iter_h2_sections(content_md):
        if title in wanted and title not in seen:
            chunks.append(block.strip())
            seen.add(title)
    return "\n\n".join(chunks)


def theory_for_task(slug: str, *, level_number: int | None = None) -> str:
    """Task playground theory — excerpts from the same level markdown as /theory/<n>/."""
    from apps.tasks.theory_content import THEORY_CONTENT

    headings = TASK_THEORY_HEADINGS.get(slug)
    if not headings:
        return ""
    if level_number is None:
        # Infer: try each level's content until headings match.
        for content in THEORY_CONTENT.values():
            excerpt = extract_sections_by_titles(content, headings)
            if excerpt:
                return excerpt
        return ""
    content = THEORY_CONTENT.get(level_number, "")
    return extract_sections_by_titles(content, headings)


def level_toc_sections(content_md: str) -> list[dict[str, str]]:
    return [
        {"title": re.sub(r"[*_`]+", "", title).strip(), "anchor": heading_anchor(title)}
        for title, _ in iter_h2_sections(content_md)
    ]
