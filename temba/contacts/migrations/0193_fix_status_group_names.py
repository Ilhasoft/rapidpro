# Generated by Django 5.1 on 2024-10-09 19:41

from django.db import migrations
from django.db.models import F, Value
from django.db.models.functions import Concat


def fix_status_group_names(apps, schema_editor):  # pragma: no cover
    ContactGroup = apps.get_model("contacts", "ContactGroup")
    num_updated = 0

    while True:
        id_batch = list(
            ContactGroup.objects.filter(group_type__in=("A", "B", "S", "V"))
            .exclude(name__startswith="\\")
            .values_list("id", flat=True)[:1000]
        )
        if not id_batch:
            break

        ContactGroup.objects.filter(id__in=id_batch).update(name=Concat(Value("\\"), F("name")))
        num_updated += len(id_batch)

    if num_updated:
        print(f"Updated {num_updated} status group names")


class Migration(migrations.Migration):

    dependencies = [("contacts", "0192_alter_contactnote_text")]

    operations = [migrations.RunPython(fix_status_group_names, migrations.RunPython.noop)]
