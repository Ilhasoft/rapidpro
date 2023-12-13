# Generated by Django 2.2.10 on 2020-12-04 17:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contacts", "0128_squashed"),
        ("airtime", "0015_squashed"),
    ]

    operations = [
        migrations.AddField(
            model_name="airtimetransfer",
            name="contact",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="airtime_transfers", to="contacts.Contact"
            ),
        ),
    ]
