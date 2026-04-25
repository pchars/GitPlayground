from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.users.models import PointLedgerEntry, UserProfile


class Command(BaseCommand):
    help = "Сравнивает сумму журнала баллов с UserProfile.total_points и печатает расхождения."

    def handle(self, *args, **options):
        mismatches = 0
        for profile in UserProfile.objects.select_related("user"):
            ledger_sum = (
                PointLedgerEntry.objects.filter(user=profile.user).aggregate(s=Sum("delta")).get("s") or 0
            )
            if ledger_sum != profile.total_points:
                mismatches += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"user_id={profile.user_id} profile={profile.total_points} ledger_sum={ledger_sum} "
                        f"delta={ledger_sum - profile.total_points}"
                    )
                )
        if mismatches == 0:
            self.stdout.write(self.style.SUCCESS("Все профили согласованы с суммой журнала (или журнал пуст)."))
        else:
            self.stdout.write(self.style.ERROR(f"Найдено расхождений: {mismatches}"))
