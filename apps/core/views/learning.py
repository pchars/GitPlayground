"""Task list and theory pages (book TOC + one page per level)."""

from __future__ import annotations

import re
from collections import defaultdict

import markdown
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from apps.core.services import (
    get_next_optional_track_task_for_user,
    get_next_unlockable_task_for_user,
)
from apps.progress.models import TaskCompletion
from apps.tasks.models import Level, Task
from apps.tasks.theory_extract import level_toc_sections, theory_for_task

THEORY_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def render_theory_markdown(content_md: str) -> str:
    if not content_md:
        return ""
    rendered = markdown.markdown(content_md, extensions=THEORY_MARKDOWN_EXTENSIONS)
    rendered = rendered.replace("<table>", '<div class="theory-table-wrap"><table>')
    rendered = rendered.replace("</table>", "</table></div>")
    return _ensure_heading_ids(rendered)


def _ensure_heading_ids(html: str) -> str:
    """Force h2/h3 ids to match heading_anchor() used in the book TOC."""
    import html as html_lib

    def repl(match: re.Match[str]) -> str:
        tag, attrs, text = match.group(1), match.group(2), match.group(3)
        plain = re.sub(r"<[^>]+>", "", text)
        plain = html_lib.unescape(plain)
        plain = re.sub(r"[*_`]+", "", plain).strip()
        anchor = slugify(plain, allow_unicode=True)
        if not anchor:
            return match.group(0)
        attrs = re.sub(r'\s*id="[^"]*"', "", attrs)
        return f'<{tag} id="{anchor}"{attrs}>{text}</{tag}>'

    return re.sub(r"<(h[23])([^>]*)>(.*?)</\1>", repl, html, flags=re.I | re.S)


def task_theory_html(slug: str, *, level_number: int | None = None) -> str:
    return render_theory_markdown(theory_for_task(slug, level_number=level_number))


def _level_overview_markdown(level: Level) -> str:
    """Prefer THEORY_CONTENT so chapter pages match playground excerpts without a reseed."""
    from apps.tasks.theory_content import THEORY_CONTENT

    content = THEORY_CONTENT.get(level.number, "")
    if content.strip():
        return content
    theory = getattr(level, "theory", None)
    return (theory.content_md if theory else "") or ""


def _chapter_payload(level: Level) -> dict:
    content_md = _level_overview_markdown(level)
    return {
        "level": level,
        "sections": level_toc_sections(content_md),
        "has_content": bool(content_md.strip()),
    }


@login_required
def tasks_list(request, level_number=None):
    levels = Level.objects.prefetch_related("tasks").order_by("number")
    completed_ids = set(
        TaskCompletion.objects.filter(user=request.user).values_list("task_id", flat=True)
    )

    task_qs = (
        Task.objects.select_related("level")
        .filter(platform=Task.Platform.GITHUB)
        .order_by("level__number", "order")
    )
    all_tasks = list(task_qs)
    next_main_task = get_next_unlockable_task_for_user(request.user)
    next_optional_task = get_next_optional_track_task_for_user(request.user)
    active_task_ids = {
        task.id
        for task in (next_main_task, next_optional_task)
        if task is not None
    }

    grouped = defaultdict(list)
    for task in all_tasks:
        if task.id in completed_ids:
            status = "completed"
        elif task.id in active_task_ids:
            status = "active"
        else:
            status = "locked"
        grouped[task.level.number].append(
            {
                "task": task,
                "status": status,
                "task_route_id": task.external_id.replace(".", "_"),
            }
        )

    selected_level = None
    if level_number is not None:
        selected_level = get_object_or_404(Level, number=level_number)
    expanded_level_number = selected_level.number if selected_level else None

    level_rows = []
    for level in levels:
        row_tasks = grouped[level.number]
        row_total = len(row_tasks)
        row_completed = sum(1 for item in row_tasks if item["status"] == "completed")
        row_active = sum(1 for item in row_tasks if item["status"] == "active")
        row_pct = round((row_completed / row_total) * 100) if row_total else 0
        level_rows.append(
            {
                "level": level,
                "tasks": row_tasks,
                "total": row_total,
                "completed": row_completed,
                "active_count": row_active,
                "progress_pct": row_pct,
            }
        )

    total_tasks = len(all_tasks)
    completed_tasks = len(completed_ids)
    overall_pct = round((completed_tasks / total_tasks) * 100) if total_tasks else 0

    return render(
        request,
        "core/tasks.html",
        {
            "level_rows": level_rows,
            "selected_level": selected_level,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overall_pct": overall_pct,
            "expanded_level_number": expanded_level_number,
        },
    )


@login_required
def theory_home(request):
    """Book table of contents: levels as chapters, ## headings as section links."""
    chapters = []
    for level in Level.objects.prefetch_related("theory").order_by("number"):
        payload = _chapter_payload(level)
        if payload["has_content"]:
            chapters.append(payload)
    return render(request, "core/theory_home.html", {"chapters": chapters})


@login_required
def theory_detail(request, level_id):
    """One level = one theory page (full markdown)."""
    from apps.tasks.theory_content import LEVEL_DIAGRAMS

    level = get_object_or_404(Level.objects.prefetch_related("theory"), number=level_id)
    content_md = _level_overview_markdown(level)
    diagram_mermaid = (getattr(level, "theory", None) and level.theory.diagram_mermaid) or LEVEL_DIAGRAMS.get(
        level.number, ""
    )
    return render(
        request,
        "core/theory_chapter.html",
        {
            "level": level,
            "rendered_md": render_theory_markdown(content_md),
            "diagram_mermaid": diagram_mermaid,
        },
    )
