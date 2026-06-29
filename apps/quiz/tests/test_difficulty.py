"""Тесты классификации и баланса сложности банка квиза."""

from __future__ import annotations

from collections import Counter

from django.test import SimpleTestCase

from apps.quiz.difficulty import (
    classify_command_difficulty,
    classify_concept_difficulty,
)
from apps.quiz.question_generator import iter_packed_questions


class DifficultyClassifierTests(SimpleTestCase):
    def test_basic_commands_are_easy(self):
        self.assertEqual(classify_command_difficulty("git init"), "easy")
        self.assertEqual(classify_command_difficulty("git status"), "easy")
        self.assertEqual(classify_command_difficulty("git add"), "easy")

    def test_plumbing_commands_are_hard(self):
        self.assertEqual(classify_command_difficulty("git hash-object"), "hard")
        self.assertEqual(classify_command_difficulty("git write-tree"), "hard")
        self.assertEqual(classify_command_difficulty("git cat-file"), "hard")

    def test_workflow_commands_are_medium(self):
        self.assertEqual(classify_command_difficulty("git rebase -i"), "medium")
        self.assertEqual(classify_command_difficulty("git reset --hard"), "medium")
        self.assertEqual(classify_command_difficulty("git stash pop"), "medium")

    def test_fundamentals_concepts_are_easy(self):
        self.assertEqual(
            classify_concept_difficulty(
                "Что означает «staging area» (индекс)?",
                "Промежуточная область перед коммитом, куда попадает git add",
            ),
            "easy",
        )
        self.assertEqual(
            classify_concept_difficulty(
                "Что такое «fast-forward» merge?",
                "Ветка просто продвигается вперёд без отдельного merge-коммита",
            ),
            "easy",
        )

    def test_internals_concepts_are_hard(self):
        self.assertEqual(
            classify_concept_difficulty(
                "Что делает `git hash-object`?",
                "Вычисляет SHA-1 для данных и может записать blob в object database",
            ),
            "hard",
        )


class DifficultyBalanceTests(SimpleTestCase):
    def test_bank_is_not_skewed_to_hard(self):
        rows = iter_packed_questions()
        counts = Counter(row["difficulty"] for row in rows)
        total = len(rows)
        hard_ratio = counts["hard"] / total
        easy_ratio = counts["easy"] / total
        medium_ratio = counts["medium"] / total

        self.assertLessEqual(hard_ratio, 0.30, msg=f"Too many hard questions: {hard_ratio:.1%}")
        self.assertGreaterEqual(easy_ratio, 0.30, msg=f"Too few easy questions: {easy_ratio:.1%}")
        self.assertGreaterEqual(medium_ratio, 0.20, msg=f"Too few medium questions: {medium_ratio:.1%}")

    def test_each_difficulty_tier_has_questions(self):
        counts = Counter(row["difficulty"] for row in iter_packed_questions())
        self.assertGreater(counts["easy"], 100)
        self.assertGreater(counts["medium"], 80)
        self.assertGreater(counts["hard"], 40)
