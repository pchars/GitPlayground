from django.test import TestCase

from apps.achievements.models import Achievement
from apps.achievements.services import bootstrap_default_achievements


class BootstrapIdempotencyTests(TestCase):
    EXPECTED_ACTIVE_ACHIEVEMENTS = 23

    def test_bootstrap_twice_stable_count(self):
        bootstrap_default_achievements()
        n1 = Achievement.objects.filter(is_active=True).count()
        bootstrap_default_achievements()
        n2 = Achievement.objects.filter(is_active=True).count()
        self.assertEqual(n1, n2)
        self.assertEqual(n1, self.EXPECTED_ACTIVE_ACHIEVEMENTS)

    def test_bootstrap_deactivates_retired_slugs(self):
        Achievement.objects.create(
            slug="journeyman_10",
            title="Старое достижение",
            description="Устаревший порог.",
            is_active=True,
            criterion_kind=Achievement.CriterionKind.TASKS_COMPLETED,
            criterion_target=10,
        )
        bootstrap_default_achievements()
        retired = Achievement.objects.get(slug="journeyman_10")
        self.assertFalse(retired.is_active)
