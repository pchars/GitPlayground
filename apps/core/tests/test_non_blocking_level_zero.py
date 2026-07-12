from django.test import TestCase

from apps.core.services import (
    can_open_task,
    get_next_optional_track_task_for_user,
    get_next_unlockable_task_for_user,
    get_suggested_next_task_after_pass,
)
from apps.core.tests.helpers import make_level, make_task, make_user
from apps.progress.models import TaskCompletion


class NonBlockingLevelZeroTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.level0 = make_level(number=0, title="Terminal", slug="terminal")
        self.level1 = make_level(number=1, title="Git basics", slug="git-basics")
        self.task0_1 = make_task(
            self.level0,
            external_id="0.1",
            slug="sandbox-pwd",
            order=1,
            title="pwd",
            points=1,
        )
        self.task0_2 = make_task(
            self.level0,
            external_id="0.2",
            slug="sandbox-ls",
            order=2,
            title="ls",
            points=1,
        )
        self.task1_1 = make_task(
            self.level1,
            external_id="1.1",
            slug="task-1-1",
            order=1,
            title="First commit",
            points=5,
        )
        self.task1_2 = make_task(
            self.level1,
            external_id="1.2",
            slug="task-1-2",
            order=2,
            title="Second commit",
            points=5,
        )

    def test_new_user_can_start_both_level_zero_and_one(self):
        self.assertEqual(get_next_optional_track_task_for_user(self.user), self.task0_1)
        self.assertEqual(get_next_unlockable_task_for_user(self.user), self.task1_1)
        self.assertTrue(can_open_task(self.user, self.task0_1))
        self.assertTrue(can_open_task(self.user, self.task1_1))
        self.assertFalse(can_open_task(self.user, self.task0_2))
        self.assertFalse(can_open_task(self.user, self.task1_2))

    def test_incomplete_level_zero_does_not_block_level_one(self):
        TaskCompletion.objects.create(user=self.user, task=self.task0_1, points_awarded=1)

        self.assertEqual(get_next_optional_track_task_for_user(self.user), self.task0_2)
        self.assertEqual(get_next_unlockable_task_for_user(self.user), self.task1_1)
        self.assertTrue(can_open_task(self.user, self.task1_1))

    def test_level_zero_completion_suggests_next_level_zero_task(self):
        TaskCompletion.objects.create(user=self.user, task=self.task0_1, points_awarded=1)

        self.assertEqual(
            get_suggested_next_task_after_pass(self.user, self.task0_1),
            self.task0_2,
        )

    def test_level_one_completion_suggests_next_main_track_task(self):
        TaskCompletion.objects.create(user=self.user, task=self.task1_1, points_awarded=5)

        self.assertEqual(
            get_suggested_next_task_after_pass(self.user, self.task1_1),
            self.task1_2,
        )
