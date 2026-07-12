"""Task list and theory pages (book-style TOC + per-article reading)."""

from collections import defaultdict

import markdown

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.core.services import (
    get_next_optional_track_task_for_user,
    get_next_unlockable_task_for_user,
)
from apps.progress.models import TaskCompletion
from apps.tasks.models import Level, Task
from apps.tasks.task_theory import theory_for_task

THEORY_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "sane_lists", "toc"]
THEORY_OVERVIEW_SLUG = "overview"


def render_theory_markdown(content_md: str) -> str:
    if not content_md:
        return ""
    rendered = markdown.markdown(content_md, extensions=THEORY_MARKDOWN_EXTENSIONS)
    rendered = rendered.replace("<table>", '<div class="theory-table-wrap"><table>')
    return rendered.replace("</table>", "</table></div>")


def task_theory_html(slug: str) -> str:
    return render_theory_markdown(theory_for_task(slug))


def _level_overview_markdown(level: Level) -> str:
    from apps.tasks.theory_content import THEORY_CONTENT

    theory = getattr(level, "theory", None)
    return (theory.content_md if theory else "") or THEORY_CONTENT.get(level.number, "")


def theory_articles_for_level(level: Level) -> list[dict]:
    articles: list[dict] = []
    if _level_overview_markdown(level).strip():
        articles.append(
            {
                "slug": THEORY_OVERVIEW_SLUG,
                "title": "Обзор уровня",
                "subtitle": "Введение и ключевые концепции",
                "index_label": "§",
            }
        )
    for index, task in enumerate(
        Task.objects.filter(level=level, platform=Task.Platform.GITHUB).order_by("order"),
        start=1,
    ):
        if not theory_for_task(task.slug):
            continue
        articles.append(
            {
                "slug": task.slug,
                "title": task.title,
                "subtitle": f"Теория к задаче {index}",
                "index_label": str(index),
            }
        )
    return articles


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
def theory_detail(request, level_id):
    """Level theory index — table of contents only."""
    level = get_object_or_404(Level.objects.prefetch_related("theory"), number=level_id)
    toc_entries = theory_articles_for_level(level)
    levels = list(Level.objects.order_by("number"))
    prev_level = next((candidate for candidate in levels if candidate.number == level.number - 1), None)
    next_level = next((candidate for candidate in levels if candidate.number == level.number + 1), None)
    return render(
        request,
        "core/theory_index.html",
        {
            "level": level,
            "toc_entries": toc_entries,
            "prev_level": prev_level,
            "next_level": next_level,
        },
    )


@login_required
def theory_article(request, level_id, article_slug):
    """Single theory chapter (overview or per-task)."""
    from apps.tasks.theory_content import LEVEL_DIAGRAMS

    level = get_object_or_404(Level.objects.prefetch_related("theory"), number=level_id)
    articles = theory_articles_for_level(level)
    article_meta = next((item for item in articles if item["slug"] == article_slug), None)
    if article_meta is None:
        raise Http404("Theory article not found")

    if article_slug == THEORY_OVERVIEW_SLUG:
        content_md = _level_overview_markdown(level)
        article_title = "Обзор уровня"
        show_diagram = True
        diagram_mermaid = (getattr(level, "theory", None) and level.theory.diagram_mermaid) or LEVEL_DIAGRAMS.get(
            level.number, ""
        )
    else:
        task = get_object_or_404(Task, level=level, slug=article_slug, platform=Task.Platform.GITHUB)
        content_md = theory_for_task(task.slug)
        article_title = task.title
        show_diagram = False
        diagram_mermaid = ""

    article_index = next(i for i, item in enumerate(articles) if item["slug"] == article_slug)
    prev_article = articles[article_index - 1] if article_index > 0 else None
    next_article = articles[article_index + 1] if article_index + 1 < len(articles) else None

    return render(
        request,
        "core/theory_article.html",
        {
            "level": level,
            "article_slug": article_slug,
            "article_title": article_title,
            "rendered_md": render_theory_markdown(content_md),
            "show_diagram": show_diagram,
            "diagram_mermaid": diagram_mermaid,
            "prev_article": prev_article,
            "next_article": next_article,
        },
    )
