# Generated by Django 4.2.8 on 2024-01-05 15:09

import mptt.fields

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("orgs", "0133_squashed"),
        ("locations", "0029_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="boundaryalias",
            name="org",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="orgs.org"),
        ),
        migrations.AddField(
            model_name="adminboundary",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="locations.adminboundary",
            ),
        ),
        migrations.AddIndex(
            model_name="boundaryalias",
            index=models.Index(
                django.db.models.functions.text.Upper("name"),
                name="boundaryaliases_by_name",
            ),
        ),
        migrations.AddIndex(
            model_name="adminboundary",
            index=models.Index(
                django.db.models.functions.text.Upper("name"),
                name="adminboundaries_by_name",
            ),
        ),
    ]
