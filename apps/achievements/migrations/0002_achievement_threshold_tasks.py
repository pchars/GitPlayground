from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("achievements", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="achievement",
            name="threshold_tasks",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
