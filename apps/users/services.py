from django.contrib.auth.models import User
from django.utils import timezone

from apps.users.legal import PRIVACY_CONSENT_SNAPSHOT, PRIVACY_POLICY_VERSION
from apps.users.models import UserProfile


def fallback_pseudonym(user: User) -> str:
    base = f"u{user.pk}"
    candidate = base[:10]
    n = 0
    while UserProfile.objects.filter(pseudonym=candidate).exists():
        n += 1
        suffix = str(n)
        candidate = f"{base[: 10 - len(suffix)]}{suffix}"
    return candidate


def ensure_user_profile(user: User) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "pseudonym": fallback_pseudonym(user),
            "certificate_name": (user.username or "Участник")[:120],
            "learning_goal": UserProfile.LearningGoal.INTEREST,
            "knowledge_level": UserProfile.KnowledgeLevel.NONE,
            "privacy_consent_at": timezone.now(),
            "privacy_consent_version": PRIVACY_POLICY_VERSION,
            "privacy_consent_text": PRIVACY_CONSENT_SNAPSHOT,
        },
    )
    return profile
