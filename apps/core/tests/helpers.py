"""Shared factories for core tests (avoid duplicated setUp)."""

from __future__ import annotations

from django.contrib.auth.models import User

from apps.tasks.models import Level, Task, TaskAsset, TaskRevision
from apps.users.models import UserProfile


def make_user(*, username: str = "alice", password: str = "password123", points: int = 20) -> User:
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, public_nickname=username, total_points=points)
    return user


def make_level(*, number: int = 1, title: str = "L1", slug: str = "l1") -> Level:
    return Level.objects.create(number=number, title=title, slug=slug, description="d")


def make_task(
    level: Level,
    *,
    external_id: str = "1.1",
    slug: str = "task-1-1",
    order: int = 1,
    title: str = "Task",
    description: str = "desc",
    points: int = 5,
) -> Task:
    return Task.objects.create(
        external_id=external_id,
        slug=slug,
        title=title,
        description=description,
        level=level,
        order=order,
        points=points,
    )


def make_playground_bundle(
    *,
    hint_content: str = "Use git status.",
    objective: str = "Complete task one objective.",
) -> tuple[User, Level, Task, Task]:
    """Two sequential tasks + hint + revision for playground API tests."""
    user = make_user()
    level = make_level()
    task1 = make_task(level, external_id="1.1", slug="task-1-1", order=1, title="Task 1", points=5)
    task2 = make_task(level, external_id="1.2", slug="task-1-2", order=2, title="Task 2", points=10)
    TaskAsset.objects.create(
        task=task1,
        asset_type=TaskAsset.AssetType.HINT,
        path="hints/hint1.txt",
        sort_order=1,
        content=hint_content,
    )
    TaskRevision.objects.create(
        task=task1,
        version=1,
        is_active=True,
        objective=objective,
        steps=["Step one", "Step two"],
        expected_state="Expected repo state.",
        validator_notes="Validator checks repository status.",
    )
    return user, level, task1, task2
