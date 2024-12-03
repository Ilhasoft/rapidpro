# Generated by Django 4.2.3 on 2023-11-23 11:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0013_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatetranslation",
            name="components",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="params",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="templatetranslation",
            name="content",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="templatetranslation",
            name="status",
            field=models.CharField(
                choices=[
                    ("A", "approved"),
                    ("P", "pending"),
                    ("R", "rejected"),
                    ("U", "unsupported_language"),
                    ("X", "unsupported_components"),
                ],
                default="P",
                max_length=1,
            ),
        ),
    ]
