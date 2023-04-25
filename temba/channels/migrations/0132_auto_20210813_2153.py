# Generated by Django 3.2.6 on 2021-08-13 21:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0131_auto_20210813_1724"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="channelconnection",
            name="channelconnection_ivr_to_retry",
        ),
        migrations.AddIndex(
            model_name="channelconnection",
            index=models.Index(
                condition=models.Q(
                    ("connection_type", "V"), ("next_attempt__isnull", False), ("status__in", ("Q", "E"))
                ),
                fields=["next_attempt"],
                name="channelconnection_ivr_to_retry",
            ),
        ),
    ]
