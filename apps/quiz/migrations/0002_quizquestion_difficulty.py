from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizquestion",
            name="difficulty",
            field=models.CharField(
                choices=[("easy", "Легкий"), ("medium", "Средний"), ("hard", "Тяжелый")],
                db_index=True,
                default="medium",
                max_length=10,
            ),
        ),
    ]
