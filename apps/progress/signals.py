from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.achievements.services import evaluate_achievements_for_user
from apps.progress.models import TaskCompletion


@receiver(post_save, sender=TaskCompletion)
def on_task_completion(sender, instance: TaskCompletion, created: bool, **kwargs):
    if not created:
        return
    evaluate_achievements_for_user(instance.user)
