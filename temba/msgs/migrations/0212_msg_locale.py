# Generated by Django 4.0.8 on 2023-01-25 18:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("msgs", "0211_alter_broadcast_base_language_and_translations"),
    ]

    operations = [
        migrations.AddField(
            model_name="msg",
            name="locale",
            field=models.CharField(max_length=6, null=True),
        ),
    ]
