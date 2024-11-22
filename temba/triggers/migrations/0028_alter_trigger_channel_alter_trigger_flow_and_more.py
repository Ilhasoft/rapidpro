# Generated by Django 4.0.9 on 2023-02-10 15:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0158_squashed"),
        ("flows", "0317_alter_flow_base_language"),
        ("triggers", "0027_squashed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trigger",
            name="channel",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="triggers", to="channels.channel"
            ),
        ),
        migrations.AlterField(
            model_name="trigger",
            name="flow",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="triggers", to="flows.flow"
            ),
        ),
        migrations.AlterField(
            model_name="trigger",
            name="keyword",
            field=models.CharField(max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name="trigger",
            name="match_type",
            field=models.CharField(
                choices=[("F", "Message starts with the keyword"), ("O", "Message contains only the keyword")],
                max_length=1,
                null=True,
            ),
        ),
    ]