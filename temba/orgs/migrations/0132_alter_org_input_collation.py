# Generated by Django 4.2.3 on 2023-11-14 15:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0131_alter_usersettings_email_verification_secret"),
    ]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="input_collation",
            field=models.CharField(
                choices=[
                    ("default", "Case insensitive (e.g. A = a)"),
                    ("confusables", "Visually similiar characters (e.g. 𝓐 = A = a = ⍺)"),
                    ("arabic_variants", "Arabic, Farsi and Pashto equivalents (e.g. ي = ی = ۍ)"),
                ],
                default="default",
                max_length=32,
            ),
        ),
    ]
