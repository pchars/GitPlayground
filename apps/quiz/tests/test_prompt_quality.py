from django.test import SimpleTestCase

from apps.quiz.prompt_quality import _SINGLE_WORD_PROMPTS, is_usable_prompt, normalize_concept_prompt
from apps.quiz.question_generator import iter_packed_questions


class PromptQualityTests(SimpleTestCase):
    def test_single_word_prompts_are_repaired(self):
        self.assertEqual(
            normalize_concept_prompt("Почему"),
            "Почему index и staging area считаются одним и тем же?",
        )

    def test_truncated_prompts_are_repaired(self):
        self.assertEqual(
            normalize_concept_prompt("Индекс (staging) в — это:"),
            "Индекс (staging) в Git — это:",
        )

    def test_question_bank_has_no_broken_prompts(self):
        prompts = [row["prompt"] for row in iter_packed_questions()]
        broken = [p for p in prompts if not is_usable_prompt(p)]
        self.assertFalse(broken, f"Broken prompts: {broken[:5]}")
        self.assertFalse(any(p.strip() in _SINGLE_WORD_PROMPTS for p in prompts))
