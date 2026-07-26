"""Facade: per-task theory excerpts from level THEORY_CONTENT."""

from __future__ import annotations

from apps.tasks.theory_extract import theory_for_task as _theory_for_task

# Back-compat for imports that expected a dict (tests / old code).
TASK_THEORY: dict[str, str] = {}


def theory_for_task(slug: str, *, level_number: int | None = None) -> str:
    return _theory_for_task(slug, level_number=level_number)
