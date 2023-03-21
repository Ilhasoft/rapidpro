# Generated by Django 4.0.8 on 2023-01-11 15:35

import mptt.fields

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("orgs", "0118_squashed"),
        ("locations", "0026_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="boundaryalias",
            name="org",
            field=models.ForeignKey(
                help_text="The org that owns this alias", on_delete=django.db.models.deletion.PROTECT, to="orgs.org"
            ),
        ),
        migrations.AddField(
            model_name="adminboundary",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                blank=True,
                help_text="The parent to this political boundary if any",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="locations.adminboundary",
            ),
        ),
    ]
