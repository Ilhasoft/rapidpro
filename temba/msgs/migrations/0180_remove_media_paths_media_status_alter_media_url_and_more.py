# Generated by Django 4.0.6 on 2022-08-01 17:31

from django.db import migrations, models

import temba.utils.uuid


class Migration(migrations.Migration):

    dependencies = [
        ("msgs", "0179_alter_media_content_type_alter_media_path"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="media",
            name="paths",
        ),
        migrations.AddField(
            model_name="media",
            name="status",
            field=models.CharField(
                choices=[("P", "Pending"), ("R", "Ready"), ("F", "Failed")], default="P", max_length=1
            ),
        ),
        migrations.AlterField(
            model_name="media",
            name="url",
            field=models.URLField(max_length=2048),
        ),
        migrations.AlterField(
            model_name="media",
            name="uuid",
            field=models.UUIDField(db_index=True, default=temba.utils.uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="media",
            name="is_ready",
            field=models.BooleanField(default=False, null=True),
        ),
    ]