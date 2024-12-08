# Generated by Django 4.1.9 on 2023-05-11 20:56

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("flows", "0318_flowstart_exclusions_alter_flowstart_include_active_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="flowstart",
            name="extra",
        ),
        migrations.RemoveField(
            model_name="flowstart",
            name="include_active",
        ),
        migrations.RemoveField(
            model_name="flowstart",
            name="restart_participants",
        ),
        migrations.AlterField(
            model_name="flowstart",
            name="created_on",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="flowstart",
            name="modified_on",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
