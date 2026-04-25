from django.test import TestCase

from apps.achievements.models import Achievement
from apps.achievements.services import bootstrap_default_achievements


class BootstrapIdempotencyTests(TestCase):
    def test_bootstrap_twice_stable_count(self):
        bootstrap_default_achievements()
        n1 = Achievement.objects.count()
        bootstrap_default_achievements()
        n2 = Achievement.objects.count()
        self.assertEqual(n1, n2)
