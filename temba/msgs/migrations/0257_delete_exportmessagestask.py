# Generated by Django 4.2.8 on 2024-03-11 21:56

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0022_remove_notification_contact_export_and_more"),
        ("msgs", "0256_delete_old_exports"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ExportMessagesTask",
        ),
    ]
