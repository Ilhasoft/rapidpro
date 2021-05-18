# Generated by Django 2.2.10 on 2020-12-04 17:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("classifiers", "0003_squashed"),
        ("orgs", "0072_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="classifier",
            name="org",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="classifiers", to="orgs.Org"
            ),
        ),
        migrations.AlterUniqueTogether(name="intent", unique_together={("classifier", "external_id")}),
    ]
