from django.test import SimpleTestCase

from apps.quiz.question_generator import question_count


class QuestionBankTests(SimpleTestCase):
    def test_at_least_two_hundred_questions(self):
        self.assertGreaterEqual(question_count(), 200)
