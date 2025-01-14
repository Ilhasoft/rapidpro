# Generated by Django 5.1.2 on 2024-10-30 19:07

import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orgs", "0155_remove_invitation_user_group_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemCount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("is_squashed", models.BooleanField(default=False)),
                ("scope", models.CharField(max_length=64)),
                ("count", models.IntegerField(default=0)),
                (
                    "org",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="counts",
                        to="orgs.org",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        models.F("org"),
                        django.contrib.postgres.indexes.OpClass("scope", name="varchar_pattern_ops"),
                        name="orgcount_org_scope",
                    ),
                    models.Index(
                        condition=models.Q(("is_squashed", False)), fields=["org", "scope"], name="orgcount_unsquashed"
                    ),
                ],
            },
        ),
    ]
