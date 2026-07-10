"""Shared factories for core tests (avoid duplicated setUp)."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.utils import timezone

from apps.tasks.models import Level, Task, TaskAsset, TaskRevision
from apps.users.legal import PRIVACY_CONSENT_SNAPSHOT, PRIVACY_POLICY_VERSION
from apps.users.models import UserProfile


def make_user(
    *,
    username: str = "alice",
    password: str = "password123",
    points: int = 20,
    pseudonym: str | None = None,
    certificate_name: str = "Alice Example",
    learning_goal: str = UserProfile.LearningGoal.INTEREST,
    knowledge_level: str = UserProfile.KnowledgeLevel.BASIC,
) -> User:
    email = username if "@" in username else f"{username}@example.com"
    user = User.objects.create_user(username=email, password=password, email=email)
    UserProfile.objects.create(
        user=user,
        pseudonym=pseudonym or username[:10],
        certificate_name=certificate_name,
        learning_goal=learning_goal,
        knowledge_level=knowledge_level,
        total_points=points,
        privacy_consent_at=timezone.now(),
        privacy_consent_version=PRIVACY_POLICY_VERSION,
        privacy_consent_text=PRIVACY_CONSENT_SNAPSHOT,
    )
    return user


def signup_form_payload(
    *,
    email: str,
    password: str,
    certificate_name: str = "Иван Иванов",
    pseudonym: str = "ivan_dev",
    learning_goal: str = UserProfile.LearningGoal.INTEREST,
    knowledge_level: str = UserProfile.KnowledgeLevel.BASIC,
    job_role: str = "",
    company_name: str = "",
    marketing_opt_in: bool = False,
    privacy_policy_accepted: bool = True,
) -> dict[str, str]:
    payload = {
        "email": email,
        "password1": password,
        "password2": password,
        "certificate_name": certificate_name,
        "pseudonym": pseudonym,
        "learning_goal": learning_goal,
        "knowledge_level": knowledge_level,
        "job_role": job_role,
        "company_name": company_name,
    }
    if marketing_opt_in:
        payload["marketing_opt_in"] = "on"
    if privacy_policy_accepted:
        payload["privacy_policy_accepted"] = "on"
    return payload


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
