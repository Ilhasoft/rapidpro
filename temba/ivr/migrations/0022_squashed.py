# Generated by Django 4.0.8 on 2023-01-11 15:35

import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contacts", "0170_squashed"),
        ("channels", "0155_squashed"),
    ]

    operations = [
        migrations.CreateModel(
            name="Call",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("direction", models.CharField(choices=[("I", "Incoming"), ("O", "Outgoing")], max_length=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("P", "Pending"),
                            ("Q", "Queued"),
                            ("W", "Wired"),
                            ("I", "In Progress"),
                            ("D", "Complete"),
                            ("E", "Errored"),
                            ("F", "Failed"),
                        ],
                        max_length=1,
                    ),
                ),
                ("external_id", models.CharField(max_length=255)),
                ("created_on", models.DateTimeField(default=django.utils.timezone.now)),
                ("modified_on", models.DateTimeField(default=django.utils.timezone.now)),
                ("started_on", models.DateTimeField(null=True)),
                ("ended_on", models.DateTimeField(null=True)),
                ("duration", models.IntegerField(null=True)),
                (
                    "error_reason",
                    models.CharField(
                        choices=[("P", "Provider"), ("B", "Busy"), ("N", "No Answer"), ("M", "Answering Machine")],
                        max_length=1,
                        null=True,
                    ),
                ),
                ("error_count", models.IntegerField(default=0)),
                ("next_attempt", models.DateTimeField(null=True)),
                (
                    "log_uuids",
                    django.contrib.postgres.fields.ArrayField(base_field=models.UUIDField(), null=True, size=None),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="calls", to="channels.channel"
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="calls", to="contacts.contact"
                    ),
                ),
                (
                    "contact_urn",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="calls", to="contacts.contacturn"
                    ),
                ),
            ],
        ),
    ]
