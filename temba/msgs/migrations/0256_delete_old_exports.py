# Generated by Django 4.2.8 on 2024-03-07 12:10

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import migrations


def delete_old_exports(apps, schema_editor):  # pragma: no cover
    ExportMessagesTask = apps.get_model("msgs", "ExportMessagesTask")
    num_deleted = 0
    num_skipped = 0

    for task in ExportMessagesTask.objects.all():
        storage_path = f"{settings.STORAGE_ROOT_DIR}/{task.org_id}/message_exports/{task.uuid}.xlsx"

        try:
            default_storage.delete(storage_path)

            task.notifications.all().delete()
            task.delete()

            num_deleted += 1
        except Exception:
            print(f"Skipping deletion of old msgs export {task.uuid} because stored file could not be deleted.")
            num_skipped += 1

    if num_deleted or num_skipped:
        print(f"Deleted {num_deleted} old msgs exports and skipped {num_skipped} old msgs exports.")


def reverse(apps, schema_editor):  # pragma: no cover
    pass


def apply_manual():  # pragma: no cover
    from django.apps import apps

    delete_old_exports(apps, None)


class Migration(migrations.Migration):
    dependencies = [
        ("msgs", "0255_exportmessagestask_item_count_and_more"),
    ]

    operations = [migrations.RunPython(delete_old_exports, reverse)]