# Generated by Django 4.2.8 on 2024-01-12 18:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0134_squashed"),
        ("msgs", "0254_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="exportmessagestask",
            name="num_records",
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name="exportmessagestask",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="orgs.org"
            ),
        ),
    ]
