# Generated by Django 2.2.10 on 2020-12-04 17:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("archives", "0013_squashed"),
        ("orgs", "0072_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="archive",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="archives", to="orgs.Org"
            ),
        ),
        migrations.AddField(
            model_name="archive",
            name="rollup",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="archives.Archive"),
        ),
        migrations.AlterUniqueTogether(
            name="archive", unique_together={("org", "archive_type", "start_date", "period")}
        ),
    ]
