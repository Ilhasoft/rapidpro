# Generated by Django 3.2.6 on 2021-08-11 20:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0129_auto_20210810_2257"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="channellog",
            index=models.Index(
                condition=models.Q(("is_error", True)),
                fields=["channel", "is_error", "-created_on"],
                name="channels_log_error_created",
            ),
        ),
    ]
