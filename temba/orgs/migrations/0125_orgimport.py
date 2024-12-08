# Generated by Django 4.1.9 on 2023-06-13 11:12

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import temba.orgs.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orgs", "0124_remove_org_stripe_customer_alter_org_country_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrgImport",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this item is active, use this instead of deleting"
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="When this item was originally created",
                    ),
                ),
                (
                    "modified_on",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="When this item was last modified",
                    ),
                ),
                ("file", models.FileField(upload_to=temba.orgs.models.get_import_upload_path)),
                (
                    "status",
                    models.CharField(
                        choices=[("P", "Pending"), ("O", "Processing"), ("C", "Complete"), ("F", "Failed")],
                        default="P",
                        max_length=1,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="The user which originally created this item",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_creations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        help_text="The user which last modified this item",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_modifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="imports", to="orgs.org"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
