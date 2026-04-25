from django.core.management.base import BaseCommand
from django.db import transaction

from apps.progress.models import LeaderboardSnapshot
from apps.users.models import UserProfile


class Command(BaseCommand):
    help = "Create leaderboard snapshots for current user ranking."

    @transaction.atomic
    def handle(self, *args, **options):
        profiles = UserProfile.objects.select_related("user").order_by("-total_points", "id")
        created = 0
        for rank, profile in enumerate(profiles, start=1):
            LeaderboardSnapshot.objects.create(
                user=profile.user,
                total_points=profile.total_points,
                rank=rank,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} leaderboard snapshots."))
