# Generated by Django 5.1 on 2024-08-19 19:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0046_alter_apitoken_role"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="apitoken",
            name="role",
        ),
    ]
