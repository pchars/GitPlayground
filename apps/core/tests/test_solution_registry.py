"""Fast golden-solution registry checks without the sandbox."""

from django.test import SimpleTestCase

from apps.core.tests.test_task_solvability import SOLUTIONS
from apps.tasks.management.commands.seed_initial_data import TASK_BLUEPRINTS


class SolutionRegistryTests(SimpleTestCase):
    def test_solutions_cover_every_blueprint_slug(self):
        slugs = [slug for level_tasks in TASK_BLUEPRINTS.values() for slug, _, _ in level_tasks]
        missing = sorted(slug for slug in slugs if slug not in SOLUTIONS)
        extra = sorted(slug for slug in SOLUTIONS if slug not in slugs)
        self.assertFalse(missing, f"No intended solution for slugs: {missing}")
        self.assertFalse(extra, f"Stale SOLUTIONS entries: {extra}")
