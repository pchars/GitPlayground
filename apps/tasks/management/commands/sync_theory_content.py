from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tasks.models import Level, TheoryBlock

from apps.tasks.management.commands.seed_initial_data import LEVEL_DIAGRAMS, LEVELS, THEORY_CONTENT


class Command(BaseCommand):
    help = (
        "Обновить в БД только блоки теории (markdown + mermaid) из встроенного THEORY_CONTENT. "
        "Задачи и прогресс не трогаются. После правок теории в коде запустите эту команду."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать существующую теорию в БД встроенным fallback-контентом.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        force = bool(options.get("force"))
        done = 0
        for level_number, level_title, _task_count in LEVELS:
            level = Level.objects.filter(number=level_number).first()
            if not level:
                self.stderr.write(
                    self.style.WARNING(
                        f"Уровень {level_number} не найден в БД — выполните сначала: manage.py seed_initial_data"
                    )
                )
                continue
            existing = TheoryBlock.objects.filter(level=level).first()
            if existing and not force:
                self.stdout.write(f"  уровень {level_number}: SKIP (уже есть в БД)")
                continue
            TheoryBlock.objects.update_or_create(
                level=level,
                defaults={
                    "title": f"Теория: {level_title}",
                    "content_md": THEORY_CONTENT[level_number],
                    "diagram_mermaid": LEVEL_DIAGRAMS[level_number],
                },
            )
            done += 1
            self.stdout.write(f"  уровень {level_number}: OK")
        mode = "force" if force else "safe"
        self.stdout.write(self.style.SUCCESS(f"Теория обновлена для уровней: {done}/{len(LEVELS)} (mode={mode})."))
