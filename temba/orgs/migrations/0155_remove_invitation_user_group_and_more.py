# Generated by Django 5.1 on 2024-10-16 22:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("orgs", "0154_backfill_invitation_role")]

    operations = [
        migrations.RemoveField(model_name="invitation", name="user_group"),
        migrations.RemoveField(model_name="usersettings", name="team"),
    ]
