"""Task list and per-level theory pages."""

from collections import defaultdict

import markdown

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.core.services import get_next_unlockable_task_for_user
from apps.progress.models import TaskCompletion
from apps.tasks.models import Level, Task


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
    # The active task is the first incomplete task in the linear track (same logic as
    # opening the playground; see apps.core.services.get_next_unlockable_task_for_user).
    next_task = get_next_unlockable_task_for_user(request.user)
    next_unlocked_id = next_task.id if next_task else None

    grouped = defaultdict(list)
    for task in all_tasks:
        status = "completed" if task.id in completed_ids else "locked"
        if next_unlocked_id is not None and task.id == next_unlocked_id:
            status = "active"
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
    active_level_number = None
    if next_unlocked_id is not None:
        active_task = next((task for task in all_tasks if task.id == next_unlocked_id), None)
        active_level_number = active_task.level.number if active_task else None
    expanded_level_number = (
        selected_level.number
        if selected_level
        else (active_level_number or (levels[0].number if levels else None))
    )

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
    from apps.tasks.theory_content import LEVEL_DIAGRAMS, THEORY_CONTENT

    level = get_object_or_404(Level.objects.prefetch_related("theory"), number=level_id)
    theory = getattr(level, "theory", None)
    # DB first: show database content in the UI; built-in dict is fallback only.
    content_md = (theory.content_md if theory else "") or THEORY_CONTENT.get(level.number, "")
    diagram_mermaid = (theory.diagram_mermaid if theory else "") or LEVEL_DIAGRAMS.get(level.number, "")

    rendered_md = ""
    if content_md:
        rendered_md = markdown.markdown(
            content_md,
            extensions=["fenced_code", "tables", "sane_lists", "toc"],
        )
        rendered_md = rendered_md.replace("<table>", '<div class="theory-table-wrap"><table>')
        rendered_md = rendered_md.replace("</table>", "</table></div>")
    levels = list(Level.objects.order_by("number"))
    prev_level = next((candidate for candidate in levels if candidate.number == level.number - 1), None)
    next_level = next((candidate for candidate in levels if candidate.number == level.number + 1), None)
    return render(
        request,
        "core/theory_detail.html",
        {
            "level": level,
            "theory": theory,
            "diagram_mermaid": diagram_mermaid,
            "rendered_md": rendered_md,
            "prev_level": prev_level,
            "next_level": next_level,
        },
    )
