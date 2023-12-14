# Generated by Django 3.2.17 on 2023-12-14 14:56

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0011_auto_20210513_1519"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="category",
            field=models.CharField(
                choices=[
                    ("ACCOUNT_UPDATE", "account_update"),
                    ("PAYMENT_UPDATE", "payment_update"),
                    ("PERSONAL_FINANCE_UPDATE", "personal_finance_update"),
                    ("SHIPPING_UPDATE", "shipping_update"),
                    ("RESERVATION_UPDATE", "reservation_update"),
                    ("ISSUE_RESOLUTION", "issue_resolution"),
                    ("APPOINTMENT_UPDATE", "appointment_update"),
                    ("TRANSPORTATION_UPDATE", "transportation_update"),
                    ("TICKET_UPDATE", "ticket_update"),
                    ("ALERT_UPDATE", "alert_update"),
                    ("AUTO_REPLY", "auto_reply"),
                    ("TRANSACTIONAL", "transactional"),
                    ("MARKETING", "marketing"),
                    ("OTP", "otp"),
                    ("UTILITY", "utility"),
                    ("AUTHENTICATION", "authentication"),
                ],
                max_length=200,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="template_type",
            field=models.CharField(
                choices=[("MEDIA", "media"), ("INTERACTIVE", "interactive"), ("TEXT", "text")],
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="message_template_id",
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="TemplateHeader",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[("TEXT", "text"), ("IMAGE", "image"), ("DOCUMENT", "document"), ("VIDEO", "video")],
                        max_length=20,
                    ),
                ),
                ("text", models.CharField(default=None, max_length=60, null=True)),
                (
                    "translation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="headers",
                        to="templates.templatetranslation",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TemplateButton",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[("QUICK_REPLY", "quick_reply"), ("PHONE_NUMBER", "phone_number"), ("URL", "url")],
                        max_length=20,
                    ),
                ),
                ("text", models.CharField(max_length=30, null=True)),
                ("country_code", models.IntegerField(null=True)),
                ("phone_number", models.CharField(max_length=20, null=True)),
                ("url", models.CharField(max_length=2000, null=True)),
                (
                    "translation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="buttons",
                        to="templates.templatetranslation",
                    ),
                ),
            ],
        ),
    ]
