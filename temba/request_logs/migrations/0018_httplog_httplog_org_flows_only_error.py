# Generated by Django 5.0.4 on 2024-05-08 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("airtime", "0027_squashed"),
        ("channels", "0185_alter_channel_name"),
        ("classifiers", "0013_squashed"),
        ("flows", "0334_remove_flowrun_submitted_by"),
        ("orgs", "0142_alter_usersettings_user"),
        ("request_logs", "0017_squashed"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="httplog",
            index=models.Index(
                condition=models.Q(("flow__isnull", False), ("is_error", True)),
                fields=["org", "-created_on"],
                name="httplog_org_flows_only_error",
            ),
        ),
    ]
