from django.core.management.base import BaseCommand
from django.db import transaction

from apps.quiz.models import QuizQuestion
from apps.quiz.question_generator import iter_packed_questions


class Command(BaseCommand):
    help = "Загрузить банк вопросов квиза (Git, 4 варианта, уровни сложности)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Удалить все вопросы и загрузить заново",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["force"]:
            deleted, _ = QuizQuestion.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Удалено вопросов: {deleted}"))
        elif QuizQuestion.objects.exists():
            n = QuizQuestion.objects.count()
            self.stdout.write(self.style.NOTICE(f"Уже есть {n} вопросов. Используйте --force для перезагрузки."))
            return

        rows = iter_packed_questions()
        objs = [QuizQuestion(**r) for r in rows]
        QuizQuestion.objects.bulk_create(objs, batch_size=400)
        self.stdout.write(self.style.SUCCESS(f"Создано вопросов: {len(objs)}"))
