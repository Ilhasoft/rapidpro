# Generated by Django 4.0.7 on 2022-11-21 21:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0202_alter_label_label_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="msg",
            name="status",
            field=models.CharField(
                choices=[
                    ("P", "Pending"),
                    ("H", "Handled"),
                    ("Q", "Queued"),
                    ("W", "Wired"),
                    ("S", "Sent"),
                    ("D", "Delivered"),
                    ("E", "Error"),
                    ("F", "Failed"),
                ],
                db_index=True,
                default="P",
                max_length=1,
            ),
        ),
    ]
