# Generated by Django 4.1.7 on 2023-03-13 18:59

from django.db import migrations

import temba.utils.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0120_backfill_empty_configs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="config",
            field=temba.utils.models.fields.JSONAsTextField(default=dict),
        ),
    ]
