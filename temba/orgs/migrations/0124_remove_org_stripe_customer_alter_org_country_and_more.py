# Generated by Django 4.1.7 on 2023-04-06 16:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0028_alter_adminboundary_level_alter_adminboundary_name_and_more"),
        ("orgs", "0123_remove_org_plan_remove_org_plan_end_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="org",
            name="stripe_customer",
        ),
        migrations.AlterField(
            model_name="org",
            name="country",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="locations.adminboundary"
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="date_format",
            field=models.CharField(
                choices=[("D", "DD-MM-YYYY"), ("M", "MM-DD-YYYY"), ("Y", "YYYY-MM-DD")],
                default="D",
                help_text="Default formatting and parsing of dates in flows and messages.",
                max_length=1,
                verbose_name="Date Format",
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="language",
            field=models.CharField(
                choices=[
                    ("en-us", "English"),
                    ("cs", "Czech"),
                    ("es", "Spanish"),
                    ("fr", "French"),
                    ("mn", "Mongolian"),
                    ("pt-br", "Portuguese"),
                    ("ru", "Russian"),
                ],
                default="en-us",
                help_text="Default website language for new users.",
                max_length=64,
                null=True,
                verbose_name="Default Language",
            ),
        ),
    ]
