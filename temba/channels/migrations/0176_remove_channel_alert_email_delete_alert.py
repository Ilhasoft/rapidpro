# Generated by Django 4.2.3 on 2023-09-27 18:32

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0175_alter_channelevent_event_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="channel",
            name="alert_email",
        ),
        migrations.DeleteModel(
            name="Alert",
        ),
    ]
