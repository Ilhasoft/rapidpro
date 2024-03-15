# Generated by Django 3.2.17 on 2023-11-28 13:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0143_auto_20210908_2224"),
        ("request_logs", "0016_alter_httplog_sequence"),
    ]

    operations = [
        migrations.AddField(
            model_name="httplog",
            name="contact",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="http_logs", to="contacts.contact"
            ),
        ),
    ]