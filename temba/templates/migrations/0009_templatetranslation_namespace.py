# Generated by Django 2.2.20 on 2021-05-06 18:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0008_auto_20201218_1911"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatetranslation",
            name="namespace",
            field=models.CharField(default="", max_length=36),
        ),
    ]
