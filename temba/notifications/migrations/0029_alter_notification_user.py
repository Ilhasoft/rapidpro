# Generated by Django 5.1.2 on 2024-11-19 21:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0028_delete_notificationcount"),
        ("orgs", "0159_usersettings_is_system"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="notifications", to="orgs.user"
            ),
        ),
    ]
