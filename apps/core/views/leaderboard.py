"""Таблица лидеров."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.progress.models import LeaderboardSnapshot
from apps.users.models import UserProfile


@login_required
def leaderboard(request):
    latest_snapshot_at = (
        LeaderboardSnapshot.objects.order_by("-captured_at").values_list("captured_at", flat=True).first()
    )
    top_users = []
    snapshot_mode = False
    if latest_snapshot_at:
        snapshot_mode = True
        snapshots = list(
            LeaderboardSnapshot.objects.filter(captured_at=latest_snapshot_at)
            .select_related("user")
            .order_by("rank")[:50]
        )
        uid_list = [s.user_id for s in snapshots]
        profile_map = {
            p.user_id: p.public_nickname
            for p in UserProfile.objects.filter(user_id__in=uid_list).only("user_id", "public_nickname")
        }
        top_users = [
            {
                "rank": row.rank,
                "user_id": row.user_id,
                "public_nickname": profile_map.get(row.user_id, row.user.username),
                "total_points": row.total_points,
            }
            for row in snapshots
        ]
    else:
        profiles = UserProfile.objects.select_related("user").order_by("-total_points")[:50]
        top_users = [
            {
                "rank": idx + 1,
                "user_id": profile.user_id,
                "public_nickname": profile.public_nickname,
                "total_points": profile.total_points,
            }
            for idx, profile in enumerate(profiles)
        ]
    return render(
        request,
        "core/leaderboard.html",
        {"top_users": top_users, "snapshot_mode": snapshot_mode, "captured_at": latest_snapshot_at},
    )
