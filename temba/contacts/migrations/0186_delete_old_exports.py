# Generated by Django 4.2.8 on 2024-03-07 12:42

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import migrations


def delete_old_exports(apps, schema_editor):  # pragma: no cover
    ExportContactsTask = apps.get_model("contacts", "ExportContactsTask")
    num_deleted = 0
    num_skipped = 0

    for task in ExportContactsTask.objects.all():
        storage_paths = [
            f"{settings.STORAGE_ROOT_DIR}/{task.org_id}/contact_exports/{task.uuid}.xlsx",
            f"{settings.STORAGE_ROOT_DIR}/{task.org_id}/contact_exports/{task.uuid}.csv",
        ]

        deleted = False
        for storage_path in storage_paths:
            try:
                default_storage.delete(storage_path)
                deleted = True
            except Exception:
                pass

        if not deleted:
            print(f"Skipping deletion of old contacts export {task.uuid} because stored file could not be deleted.")
            num_skipped += 1
        else:
            task.notifications.all().delete()
            task.delete()

            num_deleted += 1

    if num_deleted or num_skipped:
        print(f"Deleted {num_deleted} old contacts exports and skipped {num_skipped} old contacts exports.")


def reverse(apps, schema_editor):  # pragma: no cover
    pass


def apply_manual():  # pragma: no cover
    from django.apps import apps

    delete_old_exports(apps, None)


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0185_exportcontactstask_item_count_and_more"),
    ]

    operations = [migrations.RunPython(delete_old_exports, reverse)]
